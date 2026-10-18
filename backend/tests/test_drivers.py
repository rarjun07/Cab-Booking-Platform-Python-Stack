from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

from fastapi import HTTPException
from geoalchemy2 import WKTElement
import pytest
from sqlalchemy import delete, event, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.drivers import accept_ride
from app.models import Driver, Ride, RideDecline, User

VEHICLE = {"make": "Maruti", "model": "Dzire", "plate": "DL-DEMO-001"}
LOCATION = {"latitude": 28.614, "longitude": 77.209}


def add_driver(db, *, longitude=77.209, latitude=28.614, status="active", age_seconds=0):
    user = User(name="Demo Driver", email=f"{uuid4()}@example.com", role="driver", password_hash="unused-test-hash")
    db.add(user)
    db.flush()
    driver = Driver(user_id=user.id, vehicle_info=VEHICLE, status=status,
                    current_location=WKTElement(f"POINT({longitude} {latitude})", srid=4326),
                    location_updated_at=datetime.now(timezone.utc) - timedelta(seconds=age_seconds))
    db.add(driver)
    db.flush()
    return user, driver


def add_ride(db, rider_id, *, longitude=77.209, latitude=28.6139, driver_id=None, status="requested"):
    ride = Ride(rider_id=rider_id, driver_id=driver_id, status=status,
                pickup_point=WKTElement(f"POINT({longitude} {latitude})", srid=4326),
                drop_point=WKTElement("POINT(77.2295 28.6129)", srid=4326), fare_estimate=Decimal("104.38"),
                distance_meters=3982, duration_secs=396)
    db.add(ride)
    db.flush()
    return ride


@pytest.fixture
def rider(client, account):
    result = client.post("/api/auth/register", json=account)
    assert result.status_code == 201
    from uuid import UUID
    return UUID(result.json()["id"])


@pytest.fixture
def driver_account(client, account):
    account["role"] = "driver"
    result = client.post("/api/auth/register", json=account)
    assert result.status_code == 201
    return result.json()


@pytest.fixture
def online_driver(client, driver_account):
    assert client.put("/api/drivers/me", json={"vehicle_info": VEHICLE}).status_code == 200
    result = client.post("/api/drivers/me/availability", json={"status": "active", "location": LOCATION})
    assert result.status_code == 200 and result.json()["available_for_matching"]
    return driver_account


@pytest.fixture
def requested_ride(db):
    rider = User(name="Demo Rider", email=f"{uuid4()}@example.com", role="rider", password_hash="unused-test-hash")
    db.add(rider)
    db.flush()
    return add_ride(db, rider.id)


def test_profile_owned_upsert_and_availability_lifecycle(client, driver_account, db):
    assert client.get("/api/drivers/me").json() is None
    assert client.post("/api/drivers/me/availability", json={"status": "active", "location": LOCATION}).status_code == 404
    assert client.put("/api/drivers/me", json={"vehicle_info": VEHICLE, "verified": True}).status_code == 422
    saved = client.put("/api/drivers/me", json={"vehicle_info": VEHICLE}).json()
    assert saved["status"] == "offline" and saved["verified"] is False
    assert client.post("/api/drivers/me/availability", json={"status": "active"}).status_code == 422
    assert client.post("/api/drivers/me/availability", json={"status": "active", "location": {"latitude": 91, "longitude": 0}}).status_code == 422
    online = client.post("/api/drivers/me/availability", json={"status": "active", "location": LOCATION}).json()
    assert online["current_location"] == LOCATION and online["location_expires_at"]
    offline = client.post("/api/drivers/me/availability", json={"status": "offline"}).json()
    assert offline["current_location"] is None and offline["location_updated_at"] is None
    assert not offline["available_for_matching"]
    assert db.scalar(select(func.count()).select_from(Driver)) == 1


def test_twenty_nearby_offers_read_coordinates_in_one_query(client, online_driver, requested_ride, db):
    for _ in range(19): add_ride(db, requested_ride.rider_id)
    db.flush()
    statements = []
    connection = db.connection()
    def record(conn, cursor, statement, parameters, context, executemany):
        if "st_x(" in statement.lower(): statements.append(statement)
    event.listen(connection, "before_cursor_execute", record)
    try:
        result = client.get("/api/drivers/me/offers")
        assert result.status_code == 200 and len(result.json()) == 20
        assert len(statements) == 1
        assert result.json()[0]["ride"]["pickup"] == {"latitude": 28.6139, "longitude": 77.209}
    finally:
        event.remove(connection, "before_cursor_execute", record)


def test_profile_vehicle_validation_and_verified_cannot_be_self_assigned(client, driver_account, db):
    bad = {**VEHICLE, "make": "  "}
    assert client.put("/api/drivers/me", json={"vehicle_info": bad}).status_code == 422
    client.put("/api/drivers/me", json={"vehicle_info": VEHICLE})
    driver = db.scalar(select(Driver))
    driver.verified = True
    db.flush()
    changed = client.put("/api/drivers/me", json={"vehicle_info": {**VEHICLE, "plate": "DL-DEMO-002"}})
    assert changed.status_code == 200 and changed.json()["verified"] is False


def test_legacy_incomplete_vehicle_must_be_saved_before_online(client, driver_account, db):
    from uuid import UUID
    db.add(Driver(user_id=UUID(driver_account["id"]), vehicle_info={}))
    db.flush()
    assert client.post("/api/drivers/me/availability", json={"status": "active", "location": LOCATION}).status_code == 409


def test_nearby_drivers_use_meters_sort_and_exclude_ineligible(client, rider, db):
    ride = add_ride(db, rider)
    near_user, _ = add_driver(db)
    farther_user, _ = add_driver(db, longitude=77.22)
    add_driver(db, longitude=78.0)
    add_driver(db, status="offline")
    add_driver(db, age_seconds=get_settings().driver_location_max_age_seconds + 10)
    busy_user, _ = add_driver(db)
    add_ride(db, rider, driver_id=busy_user.id, status="accepted")
    declined_user, _ = add_driver(db)
    db.add(RideDecline(ride_id=ride.id, driver_id=declined_user.id))
    db.flush()
    response = client.get(f"/api/rides/{ride.id}/drivers")
    assert response.status_code == 200
    data = response.json()
    assert [row["driver_id"] for row in data] == [str(near_user.id), str(farther_user.id)]
    assert 0 < data[0]["distance_meters"] < 30 < data[1]["distance_meters"] < 5000
    assert "current_location" not in data[0] and "email" not in data[0]
    assert client.get(f"/api/rides/{uuid4()}/drivers").status_code == 404


def test_rider_cannot_inspect_other_riders_matching(client, rider, db):
    other = User(name="Other", email="private@example.com", role="rider", password_hash="unused-test-hash")
    db.add(other)
    db.flush()
    ride = add_ride(db, other.id)
    assert client.get(f"/api/rides/{ride.id}/drivers").status_code == 404


def test_current_ride_restores_only_the_riders_latest_open_request(client, rider, db):
    assert client.get("/api/rides/current").json() is None
    old = add_ride(db, rider)
    old.created_at = datetime.now(timezone.utc) - timedelta(hours=1)
    latest = add_ride(db, rider)
    latest.created_at = datetime.now(timezone.utc)
    completed = add_ride(db, rider, status="completed")
    completed.created_at = datetime.now(timezone.utc) + timedelta(seconds=1)
    other = User(name="Other", email="other-current@example.com", role="rider", password_hash="unused-test-hash")
    db.add(other)
    db.flush()
    add_ride(db, other.id)
    db.flush()
    assert client.get("/api/rides/current").json()["id"] == str(latest.id)


def test_offers_decline_and_accept_lifecycle(client, online_driver, requested_ride, db):
    first = requested_ride
    second = add_ride(db, first.rider_id, longitude=77.211)
    add_ride(db, first.rider_id, longitude=78)
    offers = client.get("/api/drivers/me/offers").json()
    assert [offer["ride"]["id"] for offer in offers] == [str(first.id), str(second.id)]
    path = f"/api/drivers/me/rides/{first.id}"
    assert client.post(f"{path}/decline").status_code == 204
    assert client.post(f"{path}/decline").status_code == 204
    assert client.post(f"{path}/accept").status_code == 409
    assert [offer["ride"]["id"] for offer in client.get("/api/drivers/me/offers").json()] == [str(second.id)]
    accepted = client.post(f"/api/drivers/me/rides/{second.id}/accept")
    assert accepted.status_code == 200 and accepted.json()["status"] == "accepted"
    assert accepted.json()["driver_id"] == online_driver["id"]
    assert client.post(f"/api/drivers/me/rides/{second.id}/accept").json()["id"] == str(second.id)
    assert client.get("/api/drivers/me/ride").json()["id"] == str(second.id)
    assert client.get("/api/drivers/me/offers").json() == []
    assert not client.get("/api/drivers/me").json()["available_for_matching"]
    assert client.post(f"{path}/accept").status_code == 409
    # Going offline does not drop the accepted assignment.
    client.post("/api/drivers/me/availability", json={"status": "offline"})
    assert client.get("/api/drivers/me/ride").json()["id"] == str(second.id)


@pytest.mark.parametrize("state", ["offline", "expired", "far", "claimed", "busy"])
def test_accept_rechecks_eligibility(client, online_driver, requested_ride, db, state):
    driver = db.scalar(select(Driver))
    if state == "offline":
        driver.status = "offline"
    elif state == "expired":
        driver.location_updated_at = datetime.now(timezone.utc) - timedelta(hours=2)
    elif state == "far":
        driver.current_location = WKTElement("POINT(78 28.6)", srid=4326)
    elif state == "claimed":
        other, _ = add_driver(db)
        requested_ride.driver_id, requested_ride.status = other.id, "accepted"
    else:
        add_ride(db, requested_ride.rider_id, driver_id=driver.user_id, status="accepted")
    db.flush()
    assert client.post(f"/api/drivers/me/rides/{requested_ride.id}/accept").status_code == 409
    if state in ("offline", "expired", "busy"):
        assert client.get("/api/drivers/me/offers").json() == []


def test_driver_does_not_read_other_drivers_current_ride(client, online_driver, requested_ride, db):
    other, _ = add_driver(db)
    requested_ride.driver_id, requested_ride.status = other.id, "accepted"
    db.flush()
    assert client.get("/api/drivers/me/ride").json() is None
    assert client.get(f"/api/rides/{requested_ride.id}/status").status_code == 403


def test_role_and_origin_protection(client, rider):
    assert client.get("/api/drivers/me").status_code == 403
    assert client.put("/api/drivers/me", json={"vehicle_info": VEHICLE}).status_code == 403
    client.post("/api/auth/logout")
    assert client.get("/api/drivers/me/offers").status_code == 401


def test_driver_writes_require_allowed_origin(client, online_driver, requested_ride):
    headers = {"Origin": "https://untrusted.example"}
    assert client.put("/api/drivers/me", json={"vehicle_info": VEHICLE}, headers=headers).status_code == 403
    assert client.post("/api/drivers/me/availability", json={"status": "offline"}, headers=headers).status_code == 403
    assert client.post(f"/api/drivers/me/rides/{requested_ride.id}/accept", headers=headers).status_code == 403
    assert client.post(f"/api/drivers/me/rides/{requested_ride.id}/decline", headers=headers).status_code == 403


def test_database_prevents_two_active_rides_for_one_driver(db, requested_ride):
    user, _ = add_driver(db)
    requested_ride.driver_id, requested_ride.status = user.id, "accepted"
    db.flush()
    with pytest.raises(IntegrityError), db.begin_nested():
        add_ride(db, requested_ride.rider_id, driver_id=user.id, status="arriving")


def test_matching_indexes_exist(db):
    indexes = dict(db.execute(text("SELECT indexname, indexdef FROM pg_indexes WHERE schemaname='public'")).all())
    assert "USING gist" in indexes["ix_drivers_location_geography"]
    assert "geography" in indexes["ix_rides_pickup_geography"]
    assert "UNIQUE INDEX" in indexes["uq_rides_active_driver"] and "WHERE" in indexes["uq_rides_active_driver"]


@pytest.mark.parametrize("scenario", ["two_drivers_one_ride", "one_driver_two_rides"])
def test_concurrent_accepts_have_one_winner(test_engine, scenario, notifications):
    # Separate committed fixtures/connections exercise real row-lock behavior.
    # test_engine is guarded by conftest to require the dedicated _test database.
    users, ride_ids = [], []
    try:
        with Session(test_engine) as setup:
            rider = User(name="Concurrent Rider", email=f"{uuid4()}@example.com", role="rider", password_hash="unused-test-hash")
            setup.add(rider)
            setup.flush()
            users.append(rider.id)
            driver_one, _ = add_driver(setup)
            driver_two, _ = add_driver(setup)
            users.extend([driver_one.id, driver_two.id])
            first, second = add_ride(setup, rider.id), add_ride(setup, rider.id)
            ride_ids.extend([first.id, second.id])
            setup.commit()
            tasks = [(driver_one.id, first.id), (driver_two.id, first.id)] if scenario == "two_drivers_one_ride" else [(driver_one.id, first.id), (driver_one.id, second.id)]
        barrier = Barrier(2)

        def attempt(task):
            with Session(test_engine) as session:
                session.execute(text("SET LOCAL lock_timeout = '5s'"))
                user = session.get(User, task[0])
                barrier.wait(timeout=5)
                try:
                    accept_ride(task[1], user, session, notifications)
                    return 200
                except HTTPException as error:
                    return error.status_code

        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(attempt, tasks))
        assert sorted(results) == [200, 409]
        with Session(test_engine) as check:
            assert check.scalar(select(func.count()).select_from(Ride).where(Ride.id.in_(ride_ids), Ride.status == "accepted")) == 1
    finally:
        with Session(test_engine) as cleanup:
            cleanup.execute(delete(RideDecline).where(RideDecline.ride_id.in_(ride_ids)))
            cleanup.execute(delete(Ride).where(Ride.id.in_(ride_ids)))
            cleanup.execute(delete(Driver).where(Driver.user_id.in_(users)))
            cleanup.execute(delete(User).where(User.id.in_(users)))
            cleanup.commit()
