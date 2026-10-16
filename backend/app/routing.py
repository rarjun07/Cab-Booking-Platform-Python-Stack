"""OSRM road routes with bounded requests, short caching, and safe error messages."""
from collections import OrderedDict
from functools import lru_cache
import math
import threading
import time

from fastapi import HTTPException
import httpx
from pydantic import ValidationError

from app.config import get_settings
from app.ride_schemas import Coordinate, RouteMetrics

USER_AGENT = "CabBookingInternship/0.3 (https://github.com/rarjun07/Cab-Booking-Platform-Python-Stack)"


class OSRMProvider:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.lock = threading.Lock()
        self.cache = OrderedDict()
        self.next_request_at = 0.0

    def route(self, pickup: Coordinate, destination: Coordinate) -> RouteMetrics:
        key = (pickup.latitude, pickup.longitude, destination.latitude, destination.longitude)
        with self.lock:
            now = time.monotonic()
            cached = self.cache.get(key)
            if cached and cached[0] > now:
                self.cache.move_to_end(key)
                return cached[1]
            if now < self.next_request_at:
                raise HTTPException(429, "Please wait a second before requesting another route.", headers={"Retry-After": "1"})
            self.next_request_at = now + 1.0
        coordinates = f"{pickup.longitude},{pickup.latitude};{destination.longitude},{destination.latitude}"
        try:
            response = httpx.get(
                f"{self.base_url}/route/v1/driving/{coordinates}",
                params={"overview": "false", "steps": "false", "radiuses": "250;250", "generate_hints": "false"},
                headers={"User-Agent": USER_AGENT}, timeout=10.0, follow_redirects=False,
            )
            data = response.json()
            if data.get("code") in ("NoRoute", "NoSegment"):
                raise HTTPException(422, "No driving route found near these coordinates. Try points closer to a road.")
            if response.status_code != 200 or data.get("code") != "Ok":
                raise HTTPException(503, "The routing service is unavailable. Please try again later.")
            route = data["routes"][0]
            metrics = RouteMetrics(distance_meters=math.ceil(float(route["distance"])),
                                   duration_secs=math.ceil(float(route["duration"])))
        except httpx.RequestError:
            raise HTTPException(503, "Could not reach the routing service. Please try again later.") from None
        except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, ValidationError):
            raise HTTPException(502, "The routing service returned an invalid route.") from None
        with self.lock:
            self.cache[key] = (time.monotonic() + 60, metrics)
            while len(self.cache) > 256:
                self.cache.popitem(last=False)
        return metrics


@lru_cache
def get_route_provider() -> OSRMProvider:
    return OSRMProvider(str(get_settings().osrm_base_url))
