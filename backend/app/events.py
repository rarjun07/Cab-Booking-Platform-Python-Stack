"""Best-effort Redis invalidations after a PostgreSQL transaction has committed."""
from functools import lru_cache
import json
import logging
import time
from typing import Annotated

from fastapi import Depends
from redis import Redis
from redis.backoff import NoBackoff
from redis.exceptions import RedisError
from redis.retry import Retry

from app.config import get_settings

logger = logging.getLogger(__name__)


def user_channel(prefix, role, user_id):
    return f"{prefix}:{role}:{user_id}"


class EventPublisher:
    def __init__(self, redis_url: str, prefix: str):
        self.prefix = prefix
        self.client = Redis.from_url(redis_url, decode_responses=True, protocol=2,
                                     socket_timeout=0.5, socket_connect_timeout=0.5,
                                     retry=Retry(NoBackoff(), 0))
        self.last_warning = float("-inf")

    def publish(self, recipients, kind, ride_id=None, *, matching=True):
        payload = {"type": kind}
        if ride_id is not None:
            payload["ride_id"] = str(ride_id)
        try:
            with self.client.pipeline(transaction=False) as pipe:
                for role, user_id in set(recipients):
                    pipe.publish(user_channel(self.prefix, role, user_id), json.dumps(payload))
                if matching:
                    # Broadcast only a generic invalidation, never a ride ID or location.
                    pipe.publish(f"{self.prefix}:matching", '{"type":"matching.changed"}')
                pipe.execute()
            return True
        except RedisError:
            if time.monotonic() - self.last_warning >= 30:
                logger.warning("Realtime notification unavailable; saved data can be refreshed through the API.")
                self.last_warning = time.monotonic()
            return False

    def ride_changed(self, ride):
        recipients = [("rider", ride.rider_id)]
        if ride.driver_id:
            recipients.append(("driver", ride.driver_id))
        return self.publish(recipients, "ride.changed", ride.id)

    def driver_changed(self, driver_id, ride=None):
        self.publish([("driver", driver_id)], "driver.changed")
        if ride is not None:
            self.publish([("rider", ride.rider_id)], "ride.location", ride.id, matching=False)

    def close(self):
        self.client.close()

    def payment_changed(self, payment, ride):
        return self.publish([("rider", ride.rider_id)], "payment.changed", ride.id, matching=False)

    def review_changed(self, ride):
        recipients = [("rider", ride.rider_id)]
        if ride.driver_id:
            recipients.append(("driver", ride.driver_id))
        return self.publish(recipients, "review.changed", ride.id, matching=False)


@lru_cache
def get_event_publisher():
    settings = get_settings()
    return EventPublisher(settings.redis_url.get_secret_value(), settings.realtime_channel_prefix)


Events = Annotated[EventPublisher, Depends(get_event_publisher)]
