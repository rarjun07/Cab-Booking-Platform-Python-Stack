from datetime import datetime, timedelta, timezone
from decimal import Decimal

import jwt
import pytest
from sqlalchemy import func, select

from app.auth import COOKIE_NAME, ISSUER
from app.config import get_settings
from app.main import app
from app.models import Ride, Driver
from app.ride_schemas import RouteMetrics, RoadRoute, RouteGeometry
from app.rides import QUOTE_AUDIENCE, calculate_fare
from app.routing import get_route_provider

PARAMETERS = {"origin": "28.6139,77.2090", "dest": "28.6129,77.2295"}


@pytest.fixture
def routing(client):
    class FakeProvider:
        calls = 0
        def route(self, pickup, destination):
            self.calls += 1
            return RoadRoute(distance_meters=4500, duration_secs=900, geometry=RouteGeometry(
                coordinates=[(pickup.longitude, pickup.latitude), (destination.longitude, destination.latitude)]))
    provider = FakeProvider()
    app.dependency_overrides[get_route_provider] = lambda: provider
    yield provider
    app.dependency_overrides.pop(get_route_provider, None)


@pytest.fixture
def rider(client, account, routing):
    response = client.post("/api/auth/register", json=account)
    assert response.status_code == 201
    return response.json()


def estimate(client):
    response = client.get("/api/rides/estimate", params=PARAMETERS)
    assert response.status_code == 200
    return response.json()


def test_fare_math_and_minimum():
    fare = calculate_fare(RouteMetrics(distance_meters=4500, duration_secs=900))
    assert fare.total == Decimal("119.00")
    assert fare.total == fare.base_fare + fare.distance_charge + fare.time_charge + fare.minimum_adjustment
    minimum = calculate_fare(RouteMetrics(distance_meters=100, duration_secs=60))
    assert minimum.total == Decimal("80.00")
    assert minimum.minimum_adjustment == Decimal("27.80")


def test_estimate_does_not_create_a_ride(client, rider, db):
    data = estimate(client)
    assert data["fare_estimate"] == "119.00"
    assert data["distance_meters"] == 4500 and data["duration_secs"] == 900
    assert data["routing_provider"] == "OSRM" and data["currency"] == "INR"
    assert db.scalar(select(func.count()).select_from(Ride)) == 0
    assert data["geometry"]["type"] == "LineString"
    # Geometry is display data, not a large signed token or a trusted fare input.
    claims = jwt.decode(data["quote_token"], get_settings().jwt_secret.get_secret_value(),
                        algorithms=["HS256"], audience=QUOTE_AUDIENCE, issuer=ISSUER)
    assert "geometry" not in claims


def test_booking_persists_server_quote_with_correct_postgis_coordinate_order(client, rider, db):
    quote = estimate(client)
    response = client.post("/api/rides/request", json={"quote_token": quote["quote_token"]})
    assert response.status_code == 201
    data = response.json()
    assert data["fare_estimate"] == "119.00" and data["status"] == "requested"
    assert data["driver_id"] is None
    stored = db.scalar(select(Ride))
    assert str(stored.rider_id) == rider["id"]
    assert stored.distance_meters == 4500 and stored.duration_secs == 900
    x, y = db.execute(select(func.ST_X(Ride.pickup_point), func.ST_Y(Ride.pickup_point))).one()
    assert x == 77.209 and y == 28.6139
    assert client.get(f'/api/rides/{data["id"]}/status').json()["id"] == data["id"]


def test_repeated_booking_uses_same_ride(client, rider, db):
    payload = {"quote_token": estimate(client)["quote_token"]}
    first, second = client.post("/api/rides/request", json=payload), client.post("/api/rides/request", json=payload)
    assert first.status_code == 201 and second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert db.scalar(select(func.count()).select_from(Ride)) == 1


@pytest.mark.parametrize("origin,dest", [("91,0", "0,0"), ("0,181", "0,0"), ("nan,0", "0,0"), ("0,inf", "0,0"), ("bad", "0,0"), ("1,2,3", "0,0"), ("1,2", "1,2")])
def test_invalid_route_rejected_before_external_request(client, rider, routing, origin, dest):
    assert client.get("/api/rides/estimate", params={"origin": origin, "dest": dest}).status_code == 422
    assert routing.calls == 0


def test_anonymous_and_driver_accounts_cannot_estimate_or_book(client, account, routing):
    assert client.get("/api/rides/estimate", params=PARAMETERS).status_code == 401
    account["role"] = "driver"
    client.post("/api/auth/register", json=account)
    assert client.get("/api/rides/estimate", params=PARAMETERS).status_code == 403
    assert client.post("/api/rides/request", json={"quote_token": "invalid"}).status_code == 403
    assert routing.calls == 0


def test_client_cannot_submit_its_own_fare(client, rider):
    response = client.post("/api/rides/request", json={"quote_token": estimate(client)["quote_token"], "fare_estimate": "0.01"})
    assert response.status_code == 422


@pytest.mark.parametrize("modification", ["expiry", "signature", "audience"])
def test_invalid_quote_rejected(client, rider, modification):
    token = estimate(client)["quote_token"]
    key = get_settings().jwt_secret.get_secret_value()
    if modification == "signature":
        header, payload, signature = token.split(".")
        token = f'{header}.{payload}.{("A" if signature[0] != "A" else "B") + signature[1:]}'
    else:
        claims = jwt.decode(token, key, algorithms=["HS256"], audience=QUOTE_AUDIENCE, issuer=ISSUER)
        if modification == "expiry":
            claims["exp"] = datetime.now(timezone.utc) - timedelta(seconds=1)
        else:
            claims["aud"] = "another-service"
        token = jwt.encode(claims, key, algorithm="HS256")
    assert client.post("/api/rides/request", json={"quote_token": token}).status_code == 422


def test_quotes_are_bound_to_rider_and_status_is_private(client, rider, account):
    quote = estimate(client)
    ride = client.post("/api/rides/request", json={"quote_token": quote["quote_token"]}).json()
    client.post("/api/auth/logout")
    account["email"] = "other-rider@example.com"
    client.post("/api/auth/register", json=account)
    assert client.post("/api/rides/request", json={"quote_token": quote["quote_token"]}).status_code == 403
    assert client.get(f'/api/rides/{ride["id"]}/status').status_code == 404


def test_auth_and_quote_tokens_are_not_interchangeable(client, rider):
    auth_token = client.cookies.get(COOKIE_NAME)
    quote_token = estimate(client)["quote_token"]
    assert client.post("/api/rides/request", json={"quote_token": auth_token}).status_code == 422
    client.cookies.clear()
    client.cookies.set(COOKIE_NAME, quote_token)
    assert client.get("/api/auth/me").status_code == 401


def test_booking_rejects_cross_origin_request(client, rider):
    payload = {"quote_token": estimate(client)["quote_token"]}
    assert client.post("/api/rides/request", json=payload, headers={"Origin": "https://untrusted.example"}).status_code == 403


def test_saved_road_route_is_private_to_rider_and_assigned_driver(client, rider, account, routing, db):
    ride = client.post("/api/rides/request", json={"quote_token": estimate(client)["quote_token"]}).json()
    path = f'/api/rides/{ride["id"]}/route'
    response = client.get(path)
    assert response.status_code == 200
    assert response.json()["geometry"]["coordinates"] == [[77.209, 28.6139], [77.2295, 28.6129]]
    calls = routing.calls
    client.post("/api/auth/logout")
    assert client.get(path).status_code == 401
    account.update(email="other-route@example.com")
    client.post("/api/auth/register", json=account)
    assert client.get(path).status_code == 404
    client.post("/api/auth/logout")
    account.update(email="route-driver@example.com", role="driver")
    driver = client.post("/api/auth/register", json=account).json()
    assert client.get(path).status_code == 404
    assert routing.calls == calls  # No upstream call before authorization.
    from uuid import UUID
    driver_id = UUID(driver["id"])
    db.add(Driver(user_id=driver_id, vehicle_info={"make": "Test", "model": "Car", "plate": "TEST123"}))
    db.flush()
    stored = db.get(Ride, UUID(ride["id"]))
    stored.driver_id = driver_id
    stored.status = "accepted"
    db.flush()
    assert client.get(path).status_code == 200
