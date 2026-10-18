"""Cookie-authenticated WebSockets with Redis pub/sub and short DB sessions."""
import asyncio
from contextlib import suppress
import json
import time
from typing import Annotated, Literal
from uuid import UUID

from anyio import to_thread
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ConfigDict, ValidationError
from redis.asyncio import Redis
from redis.backoff import NoBackoff
from redis.exceptions import RedisError
from redis.retry import Retry
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.auth import COOKIE_NAME, user_from_token
from app.config import get_settings
from app.database import get_engine
from app.driver_schemas import DriverLocationInput
from app.drivers import update_location
from app.events import Events, user_channel

router = APIRouter(tags=["Realtime"])


class LocationMessage(DriverLocationInput):
    model_config = ConfigDict(extra="forbid")
    type: Literal["location.update"]
    request_id: UUID


class RealtimeStore:
    def __init__(self, engine):
        self.engine = engine

    def authenticate(self, token, role, user_id):
        with Session(self.engine) as db:
            user = user_from_token(token, db)
            if user.id != user_id or user.role != role:
                raise HTTPException(403, "This live connection belongs to another account.")

    def location(self, token, user_id, message, events):
        with Session(self.engine) as db:
            user = user_from_token(token, db)
            if user.id != user_id or user.role != "driver":
                raise HTTPException(403, "Only the signed-in driver can share this location.")
            saved = update_location(DriverLocationInput(location=message.location), user, db, events)
            return saved.location_updated_at.isoformat()


def get_realtime_store():
    return RealtimeStore(get_engine())


def public_event(raw):
    """Ignore unknown/malformed broker data; never forward raw messages."""
    try:
        data = json.loads(raw)
        if data["type"] in ("matching.changed", "driver.changed", "wallet.changed"):
            return {"type": data["type"]}
        if data["type"] in ("ride.changed", "ride.location", "payment.changed", "review.changed"):
            return {"type": data["type"], "ride_id": str(UUID(data["ride_id"]))}
    except (ValueError, TypeError, KeyError):
        pass
    return None


async def send(websocket, data):
    # A slow client must not hold a subscription/DB recheck loop indefinitely.
    await asyncio.wait_for(websocket.send_json(data), timeout=5)


@router.websocket("/api/ws/{role}/{user_id}")
async def live_connection(websocket: WebSocket, role: Literal["rider", "driver"], user_id: UUID,
                          store: Annotated[RealtimeStore, Depends(get_realtime_store)], events: Events):
    settings = get_settings()
    if websocket.headers.get("origin") not in settings.allowed_origins:
        await websocket.close(code=1008)
        return
    token = websocket.cookies.get(COOKIE_NAME)
    try:
        await to_thread.run_sync(store.authenticate, token, role, user_id)
    except (HTTPException, OperationalError):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    tasks = set()
    try:
        async with Redis.from_url(settings.redis_url.get_secret_value(), decode_responses=True, protocol=2,
                                  socket_connect_timeout=1, socket_timeout=2,
                                  retry=Retry(NoBackoff(), 0)) as client:
            async with client.pubsub() as subscription:
                channels = [user_channel(settings.realtime_channel_prefix, role, user_id),
                            f"{settings.realtime_channel_prefix}:matching"]
                await subscription.subscribe(*channels)
                # Wait for both subscription acknowledgements before advertising ready.
                async with asyncio.timeout(3):
                    subscribed = set()
                    while len(subscribed) < len(channels):
                        reply = await subscription.get_message(timeout=1)
                        if reply and reply["type"] == "subscribe":
                            subscribed.add(reply["channel"])
                await send(websocket, {"type": "ready"})
                next_check = time.monotonic() + settings.websocket_session_check_seconds
                next_sync = time.monotonic() + settings.websocket_sync_seconds
                receive = asyncio.create_task(websocket.receive())
                broker = asyncio.create_task(subscription.get_message(ignore_subscribe_messages=True, timeout=1))
                tasks.update((receive, broker))
                while True:
                    done, _ = await asyncio.wait(tasks, timeout=settings.websocket_session_check_seconds,
                                                 return_when=asyncio.FIRST_COMPLETED)
                    now = time.monotonic()
                    # Recheck before any event/write, and while an otherwise idle socket waits.
                    if now >= next_check or receive in done or (broker in done and broker.result()):
                        try:
                            await to_thread.run_sync(store.authenticate, token, role, user_id)
                        except HTTPException:
                            await websocket.close(code=4401, reason="Session expired or revoked.")
                            return
                        next_check = time.monotonic() + settings.websocket_session_check_seconds
                    if receive in done:
                        incoming = receive.result()
                        if incoming["type"] == "websocket.disconnect":
                            return
                        text = incoming.get("text")
                        if text is None:
                            await websocket.close(code=1003)
                            return
                        if len(text.encode()) > 2048:
                            await websocket.close(code=1009)
                            return
                        try:
                            message = json.loads(text)
                            if message == {"type": "ping"}:
                                await send(websocket, {"type": "pong"})
                            elif role == "driver":
                                location = LocationMessage.model_validate(message)
                                try:
                                    updated = await to_thread.run_sync(store.location, token, user_id, location, events)
                                    await send(websocket, {"type": "location.saved", "request_id": str(location.request_id), "updated_at": updated})
                                except HTTPException as error:
                                    await send(websocket, {"type": "error", "request_id": str(location.request_id),
                                                           "status": error.status_code, "message": error.detail})
                            else:
                                await send(websocket, {"type": "error", "message": "Rider connections receive updates only."})
                        except (ValueError, TypeError, ValidationError):
                            await send(websocket, {"type": "error", "message": "Send a valid live location message."})
                        tasks.remove(receive)
                        receive = asyncio.create_task(websocket.receive())
                        tasks.add(receive)
                    if broker in done:
                        item = broker.result()
                        event = public_event(item["data"]) if item and item["type"] == "message" else None
                        if event:
                            await send(websocket, event)
                        tasks.remove(broker)
                        broker = asyncio.create_task(subscription.get_message(ignore_subscribe_messages=True, timeout=1))
                        tasks.add(broker)
                    if time.monotonic() >= next_sync:
                        await send(websocket, {"type": "sync"})
                        next_sync = time.monotonic() + settings.websocket_sync_seconds
    except (RedisError, OperationalError, TimeoutError):
        with suppress(WebSocketDisconnect, RuntimeError, OSError):
            await websocket.close(code=1013, reason="Live updates unavailable. Use Refresh.")
    except (WebSocketDisconnect, RuntimeError, OSError):
        pass
    finally:
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
