import httpx
from fastapi import HTTPException
import pytest

from app.ride_schemas import Coordinate
from app.routing import OSRMProvider

PICKUP = Coordinate(latitude=28.6139, longitude=77.209)
DESTINATION = Coordinate(latitude=28.6129, longitude=77.2295)


def test_osrm_request_coordinate_order_rounding_and_cache(monkeypatch):
    calls = []
    def get(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(200, json={"code": "Ok", "routes": [{"distance": 3981.4, "duration": 395.5}]})
    monkeypatch.setattr(httpx, "get", get)
    provider = OSRMProvider("https://router.project-osrm.org/")
    first, second = provider.route(PICKUP, DESTINATION), provider.route(PICKUP, DESTINATION)
    assert first == second and len(calls) == 1
    assert first.distance_meters == 3982 and first.duration_secs == 396
    assert calls[0][0].endswith("/77.209,28.6139;77.2295,28.6129")
    assert calls[0][1]["params"]["radiuses"] == "250;250"
    with pytest.raises(HTTPException) as error:
        provider.route(PICKUP, Coordinate(latitude=28.62, longitude=77.23))
    assert error.value.status_code == 429 and len(calls) == 1


@pytest.mark.parametrize("status,data,expected", [
    (400, {"code": "NoRoute"}, 422), (400, {"code": "NoSegment"}, 422),
    (503, {"code": "Error"}, 503), (200, {"code": "Ok", "routes": []}, 502),
    (200, {"code": "Ok", "routes": [{"distance": "nan", "duration": 20}]}, 502),
    (200, {"code": "Ok", "routes": [{"distance": -1, "duration": 20}]}, 502),
    (200, None, 502),
])
def test_osrm_failure_messages_are_safe(monkeypatch, status, data, expected):
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: httpx.Response(status, json=data))
    with pytest.raises(HTTPException) as error:
        OSRMProvider("https://router.project-osrm.org").route(PICKUP, DESTINATION)
    assert error.value.status_code == expected


def test_routing_timeout_is_not_a_fake_estimate(monkeypatch):
    def timeout(*args, **kwargs):
        raise httpx.ReadTimeout("private upstream details")
    monkeypatch.setattr(httpx, "get", timeout)
    with pytest.raises(HTTPException) as error:
        OSRMProvider("https://router.project-osrm.org").route(PICKUP, DESTINATION)
    assert error.value.status_code == 503
    assert "private" not in error.value.detail
