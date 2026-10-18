from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import socket
from threading import Thread
import time
from types import SimpleNamespace
from uuid import uuid4

from geoalchemy2 import WKTElement
import httpx
import jwt
from pydantic import SecretStr
import pytest
from redis.exceptions import RedisError
from sqlalchemy import delete
from sqlalchemy.orm import Session
import uvicorn
from websockets.exceptions import ConnectionClosedError, InvalidStatus
from websockets.sync.client import connect

from app.auth import AUDIENCE, COOKIE_NAME, ISSUER
from app.config import get_settings
from app.database import get_db
from app.events import EventPublisher, get_event_publisher
from app.drivers import profile_response
from app.main import app
from app.models import AuthSession, Driver, Review, Ride, User
from app.realtime import RealtimeStore, get_realtime_store, public_event

ORIGIN = "http://127.0.0.1:5173"


@pytest.fixture
def live_app(test_engine, monkeypatch):
    settings = get_settings()
    prefix = f"cab_booking:test:{uuid4()}"
    monkeypatch.setattr(settings, "realtime_channel_prefix", prefix)
    monkeypatch.setattr(settings, "websocket_session_check_seconds", 0.1)
    monkeypatch.setattr(settings, "websocket_sync_seconds", 1.0)
    publisher = EventPublisher(settings.redis_url.get_secret_value(), prefix)
    try:
        assert publisher.client.ping()
    except RedisError:
        pytest.fail("Realtime integration tests require the configured local Redis service.")
    users, tokens = {}, {}
    ride_id = None
    server = None
    thread = None
    listener = None
    try:
        with Session(test_engine) as db:
            for name, role in [("rider", "rider"), ("driver", "driver"), ("other", "rider"), ("other_driver", "driver")]:
                user = User(name=name, role=role, email=f"{uuid4()}@example.com", password_hash="unused-test-hash")
                db.add(user)
                db.flush()
                users[name] = user.id
                now = datetime.now(timezone.utc)
                auth_session = AuthSession(user_id=user.id, expires_at=now + timedelta(minutes=30))
                db.add(auth_session)
                db.flush()
                tokens[name] = jwt.encode({"sub": str(user.id), "jti": str(auth_session.id), "iat": now,
                                           "exp": now + timedelta(minutes=30), "iss": ISSUER, "aud": AUDIENCE},
                                          settings.jwt_secret.get_secret_value(), algorithm="HS256")
                if role == "driver":
                    db.add(Driver(user_id=user.id, vehicle_info={"make": "Maruti", "model": "Dzire", "plate": "LIVE-DEMO"},
                                  status="active", current_location=WKTElement("POINT(77.209 28.614)", srid=4326),
                                  location_updated_at=now - timedelta(seconds=2)))
            ride = Ride(rider_id=users["rider"], pickup_point=WKTElement("POINT(77.209 28.6139)", srid=4326),
                        drop_point=WKTElement("POINT(77.2295 28.6129)", srid=4326), fare_estimate=Decimal("104.38"))
            db.add(ride)
            db.flush()
            ride_id = ride.id
            db.commit()

        def request_db():
            with Session(test_engine) as db:
                yield db

        app.dependency_overrides[get_db] = request_db
        app.dependency_overrides[get_realtime_store] = lambda: RealtimeStore(test_engine)
        app.dependency_overrides[get_event_publisher] = lambda: publisher
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, log_level="error", ws_max_size=2048))
        thread = Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        deadline = time.monotonic() + 5
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started, "Test WebSocket server did not start."

        @contextmanager
        def http(name):
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", headers={"Origin": ORIGIN},
                              cookies={COOKIE_NAME: tokens[name]}, timeout=3) as client:
                yield client

        def websocket(name, *, role=None, user_id=None, token=None, origin=ORIGIN):
            selected_role = role or ("driver" if "driver" in name else "rider")
            return connect(f"ws://127.0.0.1:{port}/api/ws/{selected_role}/{user_id or users[name]}",
                           origin=origin, additional_headers={"Cookie": f"{COOKIE_NAME}={tokens[name] if token is None else token}"},
                           open_timeout=3, close_timeout=1)

        yield SimpleNamespace(users=users, tokens=tokens, ride_id=ride_id, http=http, ws=websocket,
                              publisher=publisher, prefix=prefix, engine=test_engine)
    finally:
        if server:
            server.should_exit = True
        if thread:
            thread.join(timeout=5)
            assert not thread.is_alive(), "Test server did not shut down."
        if listener:
            listener.close()
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_realtime_store, None)
        app.dependency_overrides.pop(get_event_publisher, None)
        publisher.close()
        with Session(test_engine) as cleanup:
            cleanup.execute(delete(Review).where(Review.ride_id == ride_id))
            cleanup.execute(delete(Ride).where(Ride.rider_id.in_(list(users.values()))))
            cleanup.execute(delete(Driver).where(Driver.user_id.in_(list(users.values()))))
            cleanup.execute(delete(User).where(User.id.in_(list(users.values()))))
            cleanup.commit()


def receive_kind(ws, kind):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        data = json.loads(ws.recv(timeout=max(0.01, deadline - time.monotonic())))
        if data["type"] == kind:
            return data
    pytest.fail(f"No {kind} event received.")


@pytest.mark.parametrize("case", ["missing_cookie", "wrong_id", "wrong_role", "bad_origin", "bad_token", "expired"])
def test_websocket_rejects_unauthorized_connections(live_app, case):
    options = {}
    if case == "missing_cookie":
        options["token"] = ""
    elif case == "wrong_id":
        options["user_id"] = live_app.users["other"]
    elif case == "wrong_role":
        options["role"] = "driver"
    elif case == "bad_origin":
        options["origin"] = "https://untrusted.example"
    elif case == "bad_token":
        options["token"] = "invalid"
    else:
        settings = get_settings()
        claims = jwt.decode(live_app.tokens["rider"], settings.jwt_secret.get_secret_value(), algorithms=["HS256"], audience=AUDIENCE)
        claims["exp"] = datetime.now(timezone.utc) - timedelta(seconds=1)
        options["token"] = jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm="HS256")
    with pytest.raises(InvalidStatus) as error:
        with live_app.ws("rider", **options):
            pass
    assert error.value.response.status_code == 403


def test_redis_channels_isolate_accounts_and_global_events_have_no_private_fields(live_app):
    with live_app.ws("rider") as ws:
        assert receive_kind(ws, "ready") == {"type": "ready"}
        foreign = uuid4()
        live_app.publisher.publish([("rider", live_app.users["other"])], "ride.changed", foreign, matching=False)
        live_app.publisher.publish([("rider", live_app.users["rider"])], "ride.changed", live_app.ride_id, matching=False)
        assert receive_kind(ws, "ride.changed") == {"type": "ride.changed", "ride_id": str(live_app.ride_id)}
        live_app.publisher.driver_changed(live_app.users["driver"])
        assert receive_kind(ws, "matching.changed") == {"type": "matching.changed"}


def test_acceptance_and_trip_steps_reach_rider_and_driver(live_app):
    with live_app.ws("rider") as rider, live_app.ws("driver") as driver, live_app.http("driver") as http:
        receive_kind(rider, "ready")
        receive_kind(driver, "ready")
        path = f"/api/drivers/me/rides/{live_app.ride_id}"
        assert http.post(f"{path}/accept").status_code == 200
        assert receive_kind(rider, "ride.changed")["ride_id"] == str(live_app.ride_id)
        assert receive_kind(driver, "ride.changed")["ride_id"] == str(live_app.ride_id)
        assert http.post(f"{path}/status", json={"status": "completed"}).status_code == 409
        for step in ("arriving", "in_progress", "completed"):
            result = http.post(f"{path}/status", json={"status": step})
            assert result.status_code == 200 and result.json()["status"] == step
            assert receive_kind(rider, "ride.changed")["ride_id"] == str(live_app.ride_id)
            assert http.post(f"{path}/status", json={"status": step}).status_code == 200
        assert http.get("/api/drivers/me/ride").json() is None
        with live_app.http("rider") as rider_http:
            assert rider_http.get(f"/api/rides/{live_app.ride_id}/driver-location").json() is None


def test_driver_location_is_delivered_only_to_the_assigned_rider(live_app):
    with live_app.http("driver") as driver_http:
        assert driver_http.post(f"/api/drivers/me/rides/{live_app.ride_id}/accept").status_code == 200
    with live_app.ws("rider") as rider, live_app.ws("driver") as driver, live_app.ws("other") as outsider:
        for ws in (rider, driver, outsider):
            receive_kind(ws, "ready")
        request_id = str(uuid4())
        point = {"latitude": 28.615, "longitude": 77.210}
        driver.send(json.dumps({"type": "location.update", "request_id": request_id, "location": point}))
        assert receive_kind(driver, "location.saved")["request_id"] == request_id
        assert receive_kind(rider, "ride.location")["ride_id"] == str(live_app.ride_id)
        with live_app.http("rider") as http:
            assert http.get(f"/api/rides/{live_app.ride_id}/driver-location").json()["location"] == point
        with live_app.http("other") as http:
            assert http.get(f"/api/rides/{live_app.ride_id}/driver-location").status_code == 404
        assert json.loads(outsider.recv(timeout=3)) == {"type": "matching.changed"}
        outsider.send('{"type":"ping"}')
        event = json.loads(outsider.recv(timeout=3))
        while event["type"] == "sync":
            event = json.loads(outsider.recv(timeout=3))
        assert event == {"type": "pong"}
        driver.send(json.dumps({"type": "location.update", "request_id": str(uuid4()), "location": point}))
        assert receive_kind(driver, "error")["status"] == 429


def test_logout_closes_an_already_connected_idle_socket(live_app):
    with live_app.ws("rider") as ws, live_app.http("rider") as http:
        receive_kind(ws, "ready")
        assert http.post("/api/auth/logout").status_code == 204
        with pytest.raises(ConnectionClosedError) as error:
            ws.recv(timeout=3)
        assert error.value.rcvd.code == 4401


def test_jwt_expiry_closes_an_already_connected_socket(live_app):
    settings = get_settings()
    claims = jwt.decode(live_app.tokens["rider"], settings.jwt_secret.get_secret_value(), algorithms=["HS256"], audience=AUDIENCE)
    claims["exp"] = datetime.now(timezone.utc) + timedelta(seconds=2)
    token = jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm="HS256")
    with live_app.ws("rider", token=token) as ws:
        receive_kind(ws, "ready")
        deadline = time.monotonic() + 3
        with pytest.raises(ConnectionClosedError) as error:
            while time.monotonic() < deadline:
                ws.recv(timeout=max(0.01, deadline - time.monotonic()))
        assert error.value.rcvd.code == 4401


def test_location_http_fallback_validation_freshness_and_offline_behavior(live_app):
    path = f"/api/rides/{live_app.ride_id}/driver-location"
    with live_app.http("rider") as rider, live_app.http("driver") as driver:
        assert rider.get(path).json() is None
        assert driver.post(f"/api/drivers/me/rides/{live_app.ride_id}/accept").status_code == 200
        point = {"latitude": 28.616, "longitude": 77.211}
        assert driver.post("/api/drivers/me/location", json={"location": point}, headers={"Origin": "https://untrusted.example"}).status_code == 403
        assert driver.post("/api/drivers/me/location", json={"location": {"latitude": 91, "longitude": 0}}).status_code == 422
        assert driver.post("/api/drivers/me/location", json={"location": point, "driver_id": str(uuid4())}).status_code == 422
        assert driver.post("/api/drivers/me/location", json={"location": point}).status_code == 200
        limited = driver.post("/api/drivers/me/location", json={"location": point})
        assert limited.status_code == 429 and limited.headers["Retry-After"] == "1"
        assert rider.get(path).json()["location"] == point
        with Session(live_app.engine) as db:
            db.get(Driver, live_app.users["driver"]).location_updated_at = datetime.now(timezone.utc) - timedelta(hours=1)
            db.commit()
        assert rider.get(path).json()["location"] is None
        assert driver.post("/api/drivers/me/availability", json={"status": "offline"}).status_code == 200
        assert driver.post("/api/drivers/me/location", json={"location": point}).status_code == 409
        assert rider.get(path).json()["location"] is None


def test_trip_updates_require_the_assigned_driver_and_cannot_regress(live_app):
    path = f"/api/drivers/me/rides/{live_app.ride_id}"
    with live_app.http("driver") as driver, live_app.http("other_driver") as other, live_app.http("rider") as rider:
        assert driver.post(f"{path}/accept").status_code == 200
        assert other.post(f"{path}/status", json={"status": "arriving"}).status_code == 404
        assert rider.post(f"{path}/status", json={"status": "arriving"}).status_code == 403
        assert driver.post(f"{path}/status", json={"status": "arriving"}, headers={"Origin": "https://untrusted.example"}).status_code == 403
        assert driver.post(f"{path}/status", json={"status": "arriving", "fare_actual": "0.01"}).status_code == 422
        assert driver.post(f"{path}/status", json={"status": "requested"}).status_code == 422
        for step in ("arriving", "in_progress", "completed"):
            assert driver.post(f"{path}/status", json={"status": step}).status_code == 200
        assert driver.post(f"{path}/status", json={"status": "arriving"}).status_code == 409
        with Session(live_app.engine) as db:
            assert db.get(Ride, live_app.ride_id).fare_actual is None


def test_profile_location_fields_stay_coherent_when_another_request_goes_offline(live_app):
    with Session(live_app.engine) as reader:
        cached = reader.get(Driver, live_app.users["driver"])
        assert cached.current_location is not None
        with live_app.http("driver") as driver:
            assert driver.post("/api/drivers/me/availability", json={"status": "offline"}).status_code == 200
        result = profile_response(cached, reader)
        assert result.current_location is None and result.location_updated_at is None
        assert result.status == "offline" and not result.available_for_matching


def test_riders_cannot_write_locations_and_invalid_messages_do_not_echo_input(live_app):
    with live_app.ws("rider") as rider:
        receive_kind(rider, "ready")
        rider.send('{"type":"location.update","location":{"latitude":0,"longitude":0}}')
        assert receive_kind(rider, "error")["message"] == "Rider connections receive updates only."
    with live_app.ws("driver") as driver:
        receive_kind(driver, "ready")
        driver.send('{"private-input":')
        assert "private-input" not in json.dumps(receive_kind(driver, "error"))
        driver.send(json.dumps({"type": "location.update", "request_id": str(uuid4()), "location": {"latitude": 91, "longitude": 0}}))
        assert receive_kind(driver, "error")["message"] == "Send a valid live location message."


def test_oversized_websocket_frame_is_rejected(live_app):
    with live_app.ws("driver") as ws:
        receive_kind(ws, "ready")
        ws.send("x" * 3000)
        with pytest.raises(ConnectionClosedError) as error:
            ws.recv(timeout=3)
        assert error.value.rcvd.code == 1009


def test_redis_outage_preserves_http_writes_and_closes_live_connection(live_app, monkeypatch):
    monkeypatch.setattr(get_settings(), "redis_url", SecretStr("redis://127.0.0.1:1/0"))
    broken = EventPublisher("redis://127.0.0.1:1/0", live_app.prefix)
    app.dependency_overrides[get_event_publisher] = lambda: broken
    try:
        with live_app.http("driver") as http:
            result = http.post(f"/api/drivers/me/rides/{live_app.ride_id}/accept")
            assert result.status_code == 200 and result.json()["status"] == "accepted"
        with live_app.ws("rider") as ws:
            with pytest.raises(ConnectionClosedError) as error:
                ws.recv(timeout=3)
            assert error.value.rcvd.code == 1013
    finally:
        broken.close()


def test_live_sync_and_reconnect_restore_authorized_database_state(live_app):
    with live_app.ws("rider") as first:
        receive_kind(first, "ready")
        assert receive_kind(first, "sync") == {"type": "sync"}
    # A disconnected client misses this Pub/Sub event; reconnect uses REST state.
    with live_app.http("driver") as driver:
        assert driver.post(f"/api/drivers/me/rides/{live_app.ride_id}/accept").status_code == 200
    with live_app.ws("rider") as second, live_app.http("rider") as rider:
        receive_kind(second, "ready")
        assert rider.get("/api/rides/current").json()["status"] == "accepted"


@pytest.mark.parametrize("data", ["bad-json", "[]", '{"type":"secret","password":"never-forward"}', '{"type":"ride.changed","ride_id":"bad"}'])
def test_unknown_broker_data_is_not_forwarded(data):
    assert public_event(data) is None


def test_review_notifications_reach_only_trip_participants_without_comment_payloads(live_app):
    with live_app.http("driver") as driver:
        path = f"/api/drivers/me/rides/{live_app.ride_id}"
        assert driver.post(f"{path}/accept").status_code == 200
        for status in ("arriving", "in_progress", "completed"):
            assert driver.post(f"{path}/status", json={"status": status}).status_code == 200
    with live_app.ws("rider") as rider, live_app.ws("driver") as driver, live_app.ws("other") as outsider:
        for ws in (rider, driver, outsider):
            receive_kind(ws, "ready")
        with live_app.publisher.client.pubsub() as matching:
            matching.subscribe(f"{live_app.prefix}:matching")
            assert matching.get_message(timeout=1)["type"] == "subscribe"
            with live_app.http("rider") as http:
                result = http.post(f"/api/rides/{live_app.ride_id}/reviews", json={"rating": 5, "comment": "Private trip feedback"})
                assert result.status_code == 201
            expected = {"type": "review.changed", "ride_id": str(live_app.ride_id)}
            assert receive_kind(rider, "review.changed") == expected
            assert receive_kind(driver, "review.changed") == expected
            assert matching.get_message(timeout=0.2) is None
        # The outsider's next event must be periodic sync, not a review broadcast.
        assert json.loads(outsider.recv(timeout=2))["type"] == "sync"
        with live_app.http("driver") as http:
            summary = http.get("/api/ratings/me").json()
            assert summary["average"] == "5.00" and summary["count"] == 1
        with live_app.http("other") as http:
            assert http.get(f"/api/rides/{live_app.ride_id}/reviews").status_code == 404


def test_review_broker_messages_are_reduced_to_minimal_notification_fields():
    ride_id = str(uuid4())
    raw = json.dumps({"type": "review.changed", "ride_id": ride_id, "comment": "Do not forward", "rating": 5})
    assert public_event(raw) == {"type": "review.changed", "ride_id": ride_id}
