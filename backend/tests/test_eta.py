from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
import pytest

from app.main import app
from app.routing import get_route_provider
from app.ride_schemas import RoadRoute, RouteGeometry
from test_drivers import add_driver, add_ride, rider, driver_account, online_driver, requested_ride


@pytest.fixture
def roads():
    class Provider:
        calls = []
        def route(self, origin, dest):
            self.calls.append((origin, dest))
            return RoadRoute(distance_meters=1234, duration_secs=180, geometry=RouteGeometry(
                coordinates=[(origin.longitude, origin.latitude), (dest.longitude, dest.latitude)]))
    provider = Provider()
    provider.calls = []
    app.dependency_overrides[get_route_provider] = lambda: provider
    yield provider
    app.dependency_overrides.pop(get_route_provider, None)


def test_eta_changes_target_with_trip_progress_and_is_private(client, rider, db, roads, account):
    driver_user, driver = add_driver(db)
    ride = add_ride(db, rider, driver_id=driver.user_id, status="accepted")
    path = f"/api/rides/{ride.id}/eta"
    response = client.get(path)
    assert response.status_code == 200
    data = response.json()
    assert data["available"] and data["target"] == "pickup" and data["duration_secs"] == 180
    assert data["expires_at"] and data["location_updated_at"]
    assert roads.calls[-1][1].latitude == 28.6139
    ride.status = "in_progress"
    db.flush()
    assert client.get(path).json()["target"] == "destination"
    assert roads.calls[-1][1].longitude == 77.2295
    calls = len(roads.calls)
    client.post("/api/auth/logout")
    assert client.get(path).status_code == 401
    account.update(email="outsider-eta@example.com")
    client.post("/api/auth/register", json=account)
    assert client.get(path).status_code == 404
    assert len(roads.calls) == calls


@pytest.mark.parametrize("kind", ["offline", "expired", "missing", "unassigned", "completed"])
def test_eta_never_routes_missing_or_stale_locations(client, rider, db, roads, kind):
    _, driver = add_driver(db)
    ride = add_ride(db, rider, driver_id=driver.user_id, status="accepted")
    if kind == "offline": driver.status = "offline"
    elif kind == "expired": driver.location_updated_at = datetime.now(timezone.utc) - timedelta(hours=2)
    elif kind == "missing": driver.current_location = None
    elif kind == "unassigned": ride.driver_id = None; ride.status = "requested"
    elif kind == "completed": ride.status = "completed"
    db.flush()
    data = client.get(f"/api/rides/{ride.id}/eta").json()
    assert not data["available"]
    assert data["duration_secs"] is None and data["geometry"] is None
    assert roads.calls == []


def test_coincident_driver_and_target_have_zero_eta_without_upstream(client, rider, db, roads):
    _, driver = add_driver(db, latitude=28.6139)
    ride = add_ride(db, rider, driver_id=driver.user_id, status="accepted")
    data = client.get(f"/api/rides/{ride.id}/eta").json()
    assert data["available"] and data["duration_secs"] == 0 and data["distance_meters"] == 0
    assert roads.calls == []


def test_assigned_driver_can_read_eta_and_route_failure_is_not_a_fake_eta(client, online_driver, requested_ride, db, roads):
    from uuid import UUID
    requested_ride.driver_id = UUID(online_driver["id"])
    requested_ride.status = "accepted"
    db.flush()
    path = f"/api/rides/{requested_ride.id}/eta"
    assert client.get(path).status_code == 200
    def unavailable(*args): raise HTTPException(503, "Routing unavailable")
    roads.route = unavailable
    assert client.get(path).status_code == 503
