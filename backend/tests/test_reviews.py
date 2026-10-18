from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, ROUND_HALF_UP
import json
from threading import Barrier
from uuid import UUID, uuid4

from fastapi import HTTPException, Response
from geoalchemy2 import WKTElement
import pytest
from sqlalchemy import delete, event, func, select, text
from sqlalchemy.orm import Session

from app.auth import password_hasher
from app.models import Driver, Review, Ride, User
from app.review_schemas import ReviewInput
from app.reviews import submit_review


def add_ride(db, rider, driver, status="completed"):
    ride = Ride(rider_id=rider, driver_id=driver, status=status, fare_estimate=Decimal("104.38"),
                pickup_point=WKTElement("POINT(77.209 28.6139)", srid=4326),
                drop_point=WKTElement("POINT(77.2295 28.6129)", srid=4326))
    db.add(ride)
    db.flush()
    return ride


@pytest.fixture
def trip(client, db, account):
    registered = client.post("/api/auth/register", json=account)
    assert registered.status_code == 201
    rider = db.get(User, UUID(registered.json()["id"]))
    driver = User(name="Review Driver", email="review-driver@example.com", role="driver",
                  password_hash=password_hasher.hash(account["password"]))
    db.add(driver)
    db.flush()
    db.add(Driver(user_id=driver.id, vehicle_info={}))
    db.flush()
    return rider, driver, add_ride(db, rider.id, driver.id)


def test_both_participants_review_without_payment_and_have_private_summaries(client, db, trip, account):
    rider, driver, ride = trip
    path = f"/api/rides/{ride.id}/reviews"
    assert client.get("/api/ratings/me").json()["average"] is None
    before = client.get(path).json()
    assert before["can_review"] and before["counterpart"]["count"] == 0
    assert before["submitted"] is None and before["received"] is None
    given = client.post(path, json={"rating": 5, "comment": "  Very helpful driver.  "})
    assert given.status_code == 201
    assert given.json()["rater_id"] == str(rider.id) and given.json()["rated_id"] == str(driver.id)
    assert given.json()["comment"] == "Very helpful driver." and given.json()["created_at"]
    state = client.get(path)
    assert state.headers["cache-control"] == "no-store"
    assert not state.json()["can_review"] and state.json()["counterpart"]["average"] == "5.00"
    assert db.get(User, driver.id).rating_avg == Decimal("5.00")
    assert client.post("/api/auth/logout").status_code == 204
    assert client.post("/api/auth/login", json={"email": driver.email, "password": account["password"]}).status_code == 200
    assert client.get(path).json()["received"]["id"] == given.json()["id"]
    assert client.get("/api/ratings/me").json()["average"] == "5.00"
    returned = client.post(path, json={"rating": 4, "comment": "Polite rider"})
    assert returned.status_code == 201 and returned.json()["rated_id"] == str(rider.id)
    assert db.get(User, rider.id).rating_avg == Decimal("4.00")
    assert db.scalar(select(func.count()).select_from(Review)) == 2
    for forbidden in ("email", "password_hash", "quote_token"):
        assert forbidden not in client.get(path).text


def test_identical_retry_is_idempotent_and_conflicting_review_is_rejected(client, db, trip):
    path = f"/api/rides/{trip[2].id}/reviews"
    first = client.post(path, json={"rating": 4, "comment": "   "})
    second = client.post(path, json={"rating": 4, "comment": None})
    assert first.status_code == 201 and second.status_code == 200
    assert first.json()["id"] == second.json()["id"] and first.json()["comment"] is None
    assert client.post(path, json={"rating": 3}).status_code == 409
    assert client.post(path, json={"rating": 4, "comment": "Changed"}).status_code == 409
    assert db.scalar(select(func.count()).select_from(Review)) == 1
    assert client.get(path).json()["counterpart"]["count"] == 1


@pytest.mark.parametrize("rating", [0, 6, -1, 4.5, "5", True, None])
def test_rating_requires_whole_number_in_range(client, db, trip, rating):
    assert client.post(f"/api/rides/{trip[2].id}/reviews", json={"rating": rating}).status_code == 422
    assert db.scalar(select(func.count()).select_from(Review)) == 0


def test_body_cannot_choose_recipient_or_author_and_comment_is_bounded_plain_text(client, trip):
    path = f"/api/rides/{trip[2].id}/reviews"
    for key in ("rater_id", "rated_id", "ride_id"):
        assert client.post(path, json={"rating": 5, key: str(uuid4())}).status_code == 422
    assert client.post(path, json={"rating": 5, "comment": "x" * 2001}).status_code == 422
    comment = "<script>example plain text</script>\n" + "x" * 1950
    saved = client.post(path, json={"rating": 5, "comment": comment})
    assert saved.status_code == 201 and saved.json()["comment"] == comment


@pytest.mark.parametrize("comment", ["Invalid\x00text", "Invalid\ud800text"])
def test_invalid_postgresql_text_is_rejected_without_echoing_comment(client, db, trip, comment):
    result = client.post(f"/api/rides/{trip[2].id}/reviews", content=json.dumps({"rating": 5, "comment": comment}),
                         headers={"Content-Type": "application/json"})
    assert result.status_code == 422
    assert "input" not in result.json()["detail"][0]
    assert db.scalar(select(func.count()).select_from(Review)) == 0


@pytest.mark.parametrize("status", ["requested", "accepted", "arriving", "in_progress", "cancelled"])
def test_only_completed_rides_can_be_reviewed(client, db, trip, status):
    trip[2].status = status
    db.flush()
    path = f"/api/rides/{trip[2].id}/reviews"
    assert client.get(path).status_code == 409
    result = client.post(path, json={"rating": 5})
    assert result.status_code == 409 and "Reviews" in result.json()["detail"]


def test_origin_session_ownership_and_missing_counterpart_guards(client, db, trip, account):
    ride = trip[2]
    path = f"/api/rides/{ride.id}/reviews"
    assert client.post(path, json={"rating": 5}, headers={"Origin": "https://untrusted.example"}).status_code == 403
    ride.driver_id = None
    db.flush()
    assert client.get(path).json()["can_review"] is False
    assert client.post(path, json={"rating": 5}).status_code == 409
    ride.driver_id = trip[1].id
    db.flush()
    client.post("/api/auth/logout")
    assert client.get(path).status_code == 401
    assert client.post(path, json={"rating": 5}).status_code == 401
    assert client.get("/api/ratings/me").status_code == 401
    for role in ("rider", "driver"):
        registered = client.post("/api/auth/register", json={**account, "role": role, "email": f"outside-{role}@example.com"})
        assert registered.status_code == 201
        assert client.get(path).status_code == 404
        assert client.post(path, json={"rating": 5}).status_code == 404
        client.post("/api/auth/logout")
    assert db.scalar(select(func.count()).select_from(Review)) == 0


def test_average_is_rounded_and_counts_all_received_reviews(client, db, trip):
    rider, driver, first = trip
    for ride, rating in [(first, 4), (add_ride(db, rider.id, driver.id), 4), (add_ride(db, rider.id, driver.id), 5)]:
        assert client.post(f"/api/rides/{ride.id}/reviews", json={"rating": rating}).status_code == 201
    summary = client.get(f"/api/rides/{first.id}/reviews").json()["counterpart"]
    assert summary["count"] == 3 and summary["average"] == "4.33"
    assert db.get(User, driver.id).rating_avg == Decimal("4.33")


@pytest.mark.parametrize("scenario", ["same_retry", "conflicting_retry", "different_rides", "both_directions", "opposite_different_rides"])
def test_concurrent_reviews_preserve_uniqueness_and_cached_averages(test_engine, notifications, scenario):
    users, rides = [], []
    try:
        with Session(test_engine) as setup:
            rider = User(name="First reviewer", email=f"{uuid4()}@example.com", role="rider", password_hash="unused")
            other = User(name="Second reviewer", email=f"{uuid4()}@example.com", role="rider", password_hash="unused")
            driver = User(name="Rated driver", email=f"{uuid4()}@example.com", role="driver", password_hash="unused")
            setup.add_all([rider, other, driver])
            setup.flush()
            users = [rider.id, other.id, driver.id]
            setup.add(Driver(user_id=driver.id, vehicle_info={}))
            setup.flush()
            first = add_ride(setup, rider.id, driver.id)
            second = add_ride(setup, rider.id if scenario == "opposite_different_rides" else other.id, driver.id)
            rides = [first.id, second.id]
            tasks = [(rider.id, first.id, 5), (rider.id, first.id, 5)]
            if scenario == "conflicting_retry": tasks[1] = (rider.id, first.id, 1)
            if scenario == "different_rides": tasks[1] = (other.id, second.id, 1)
            if scenario == "both_directions": tasks[1] = (driver.id, first.id, 1)
            if scenario == "opposite_different_rides": tasks[1] = (driver.id, second.id, 1)
            setup.commit()
        barrier = Barrier(2)
        flush_barrier = Barrier(2)
        def submit(task):
            with Session(test_engine) as db:
                db.execute(text("SET LOCAL lock_timeout = '5s'"))
                user = db.get(User, task[0])
                if scenario == "opposite_different_rides":
                    # Force both recipient locks to be held before FK checks;
                    # an unnecessarily strong FOR UPDATE lock would deadlock.
                    event.listen(db, "before_flush", lambda *args: flush_barrier.wait(timeout=5), once=True)
                barrier.wait(timeout=5)
                response = Response(status_code=201)
                try:
                    submit_review(task[1], ReviewInput(rating=task[2]), user, db, response, notifications)
                    return response.status_code
                except HTTPException as error:
                    return error.status_code
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = sorted(workers.map(submit, tasks))
        expected = [200, 201] if scenario == "same_retry" else [201, 409] if scenario == "conflicting_retry" else [201, 201]
        assert results == expected
        with Session(test_engine) as check:
            for user_id in users:
                values = check.scalars(select(Review.rating).where(Review.rated_id == user_id)).all()
                average = (Decimal(sum(values)) / len(values)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if values else Decimal("0.00")
                assert check.get(User, user_id).rating_avg == average
            assert check.scalar(select(func.count()).select_from(Review).where(Review.ride_id.in_(rides))) == (1 if "retry" in scenario else 2)
    finally:
        with Session(test_engine) as cleanup:
            cleanup.execute(delete(Review).where(Review.ride_id.in_(rides)))
            cleanup.execute(delete(Ride).where(Ride.id.in_(rides)))
            cleanup.execute(delete(Driver).where(Driver.user_id.in_(users)))
            cleanup.execute(delete(User).where(User.id.in_(users)))
            cleanup.commit()
