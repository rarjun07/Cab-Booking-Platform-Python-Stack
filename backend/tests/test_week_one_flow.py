"""Day 7: exercise the connected API journey while Stripe setup is deferred.

Accounts, sessions, quotes, rides and matching use the real migrated test DB.
Routing is deterministic; notifications are silenced by conftest. The existing
realtime suite separately exercises actual TCP sockets and Redis.
"""
from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.auth import COOKIE_NAME
from app.config import get_settings
from app.main import app
from app.models import Payment, Ride
from app.payment_gateway import get_payment_gateway
from app.ride_schemas import RouteMetrics
from app.routing import get_route_provider


@pytest.fixture
def deferred_services(client, monkeypatch):
    class RouteProvider:
        calls = 0

        def route(self, pickup, destination):
            self.calls += 1
            return RouteMetrics(distance_meters=4500, duration_secs=900)

    class NoPaymentProvider:
        def create(self, *args):
            pytest.fail("Disabled checkout must not create a Stripe intent.")

        def retrieve(self, *args):
            pytest.fail("Disabled checkout must not contact Stripe.")

    provider = RouteProvider()
    for key in ("stripe_secret_key", "stripe_publishable_key", "stripe_webhook_secret"):
        monkeypatch.setattr(get_settings(), key, None)
    app.dependency_overrides[get_route_provider] = lambda: provider
    app.dependency_overrides[get_payment_gateway] = NoPaymentProvider
    try:
        yield provider
    finally:
        app.dependency_overrides.pop(get_route_provider, None)
        app.dependency_overrides.pop(get_payment_gateway, None)


def test_rider_driver_journey_with_deferred_payments(client, db, account, deferred_services):
    # Start as a rider and request a real persisted ride from a signed quote.
    rider = client.post("/api/auth/register", json=account)
    assert rider.status_code == 201
    rider_id = rider.json()["id"]
    params = {"origin": "28.6139,77.2090", "dest": "28.6129,77.2295"}
    estimated = client.get("/api/rides/estimate", params=params)
    assert estimated.status_code == 200
    quote = estimated.json()
    assert quote["fare_estimate"] == "119.00"
    booking = {"quote_token": quote["quote_token"]}
    requested = client.post("/api/rides/request", json=booking)
    assert requested.status_code == 201
    ride_id = requested.json()["id"]
    retry = client.post("/api/rides/request", json=booking)
    assert retry.status_code == 200 and retry.json()["id"] == ride_id
    assert client.get(f"/api/rides/{ride_id}/drivers").json() == []
    assert client.post("/api/auth/logout").status_code == 204

    # A separate account can accept the request through the driver endpoints.
    driver_account = {**account, "name": "Journey Driver", "email": "journey-driver@example.com", "role": "driver"}
    registered = client.post("/api/auth/register", json=driver_account)
    assert registered.status_code == 201
    driver_id = registered.json()["id"]
    vehicle = {"make": "Maruti", "model": "Dzire", "plate": "DL-JOURNEY-001"}
    assert client.put("/api/drivers/me", json={"vehicle_info": vehicle}).status_code == 200
    online = client.post("/api/drivers/me/availability", json={
        "status": "active", "location": {"latitude": 28.614, "longitude": 77.209},
    })
    assert online.status_code == 200 and online.json()["available_for_matching"]
    offers = client.get("/api/drivers/me/offers")
    assert offers.status_code == 200
    assert [offer["ride"]["id"] for offer in offers.json()] == [ride_id]
    driver_path = f"/api/drivers/me/rides/{ride_id}"
    accepted = client.post(f"{driver_path}/accept")
    assert accepted.status_code == 200
    assert accepted.json()["driver_id"] == driver_id
    assert client.get("/api/drivers/me/ride").json()["id"] == ride_id
    assert client.get("/api/drivers/me/offers").json() == []
    assert not client.get("/api/drivers/me").json()["available_for_matching"]
    assert client.get(f"/api/rides/{ride_id}/payment").status_code == 403
    assert client.post(f"{driver_path}/status", json={"status": "completed"}).status_code == 409

    for status in ("arriving", "in_progress", "completed"):
        progressed = client.post(f"{driver_path}/status", json={"status": status})
        assert progressed.status_code == 200 and progressed.json()["status"] == status
    assert client.get("/api/drivers/me/ride").json() is None
    assert client.get("/api/drivers/me").json()["available_for_matching"]
    assert client.post("/api/drivers/me/availability", json={"status": "offline"}).status_code == 200
    assert client.post("/api/auth/logout").status_code == 204

    # Login restoration works after completion, without requiring Stripe setup.
    login = {"email": account["email"], "password": account["password"]}
    signed_in = client.post("/api/auth/login", json=login)
    assert signed_in.status_code == 200 and signed_in.json()["id"] == rider_id
    restored = client.get("/api/rides/current")
    assert restored.status_code == 200
    assert restored.json()["id"] == ride_id and restored.json()["status"] == "completed"
    assert restored.json()["driver_id"] == driver_id
    assert client.get(f"/api/rides/{ride_id}/driver-location").json() is None
    assert client.get(f"/api/rides/{ride_id}/payment").json() is None
    config = client.get("/api/payments/config")
    assert config.status_code == 200
    assert config.json() == {"configured": False, "publishable_key": None, "test_mode": True}
    disabled = client.post(f"/api/rides/{ride_id}/payment-intent", json={})
    assert disabled.status_code == 503
    assert db.scalar(select(func.count()).select_from(Payment)) == 0
    assert db.get(Ride, UUID(ride_id)).fare_actual is None

    # A new request takes priority over the completed ride on the next reload.
    next_quote = client.get("/api/rides/estimate", params=params).json()
    next_ride = client.post("/api/rides/request", json={"quote_token": next_quote["quote_token"]})
    assert next_ride.status_code == 201 and next_ride.json()["id"] != ride_id
    assert client.get("/api/rides/current").json()["id"] == next_ride.json()["id"]
    assert deferred_services.calls == 2
    assert db.scalar(select(func.count()).select_from(Ride)) == 2

    # Logout invalidates the database session even if its old cookie is replayed.
    old_cookie = client.cookies.get(COOKIE_NAME)
    assert old_cookie
    assert client.post("/api/auth/logout").status_code == 204
    client.cookies.set(COOKIE_NAME, old_cookie)
    for path in ("/api/auth/me", "/api/rides/current", f"/api/rides/{ride_id}/payment"):
        assert client.get(path).status_code == 401
