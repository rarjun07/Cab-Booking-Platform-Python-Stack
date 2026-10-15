from decimal import Decimal
from uuid import uuid4

import pytest
from geoalchemy2 import WKTElement
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.models import Driver, Payment, Review, Ride, User


@pytest.fixture
def booking(db):
    rider = User(name="Rider", email="model-rider@example.com", password_hash="test-fixture-hash", role="rider")
    driver_user = User(name="Driver", email="model-driver@example.com", password_hash="test-fixture-hash", role="driver")
    db.add_all([rider, driver_user])
    db.flush()
    driver = Driver(user_id=driver_user.id, current_location=WKTElement("POINT(77.2090 28.6139)", srid=4326))
    db.add(driver)
    db.flush()
    ride = Ride(rider_id=rider.id, driver_id=driver.user_id,
                pickup_point=WKTElement("POINT(77.2090 28.6139)", srid=4326),
                drop_point=WKTElement("POINT(77.2167 28.6333)", srid=4326),
                fare_estimate=Decimal("149.90"))
    db.add(ride)
    db.flush()
    return rider, driver, ride


def test_domain_records_and_decimal_fares_round_trip(db, booking):
    rider, driver, ride = booking
    payment = Payment(ride_id=ride.id, amount=Decimal("149.90"))
    review = Review(ride_id=ride.id, rater_id=rider.id, rated_id=driver.user_id, rating=5)
    db.add_all([payment, review])
    db.flush()
    db.expire_all()
    assert db.get(Ride, ride.id).fare_estimate == Decimal("149.90")
    assert db.get(Payment, payment.id).status == "pending"
    assert db.get(Driver, driver.user_id).verified is False
    assert db.get(User, rider.id).rating_avg == Decimal("0.00")


def test_postgis_points_and_distance_in_meters(db, booking):
    _, _, ride = booking
    srid = db.scalar(select(func.ST_SRID(Ride.pickup_point)).where(Ride.id == ride.id))
    distance = db.scalar(select(func.ST_DistanceSphere(Ride.pickup_point, Ride.drop_point)).where(Ride.id == ride.id))
    assert srid == 4326
    assert 2000 < distance < 2500
    indexes = db.execute(text("SELECT indexname, indexdef FROM pg_indexes WHERE tablename IN ('drivers', 'rides')")).all()
    for expected in ("idx_drivers_current_location", "idx_rides_pickup_point", "idx_rides_drop_point"):
        assert any(name == expected and "USING gist" in definition for name, definition in indexes)


@pytest.mark.parametrize("field,value", [("fare_estimate", Decimal("-1")), ("fare_actual", Decimal("-1")), ("distance_meters", -1), ("duration_secs", -1), ("status", "unknown")])
def test_invalid_ride_values_are_rejected(db, booking, field, value):
    ride = booking[2]
    with pytest.raises(IntegrityError), db.begin_nested():
        setattr(ride, field, value)
        db.flush()


def test_coordinate_bounds_are_enforced(db, booking):
    with pytest.raises(IntegrityError), db.begin_nested():
        booking[2].pickup_point = WKTElement("POINT(200 95)", srid=4326)
        db.flush()


def test_missing_driver_foreign_key_is_rejected(db, booking):
    with pytest.raises(IntegrityError), db.begin_nested():
        booking[2].driver_id = uuid4()
        db.flush()


@pytest.mark.parametrize("rating", [0, 6])
def test_review_rating_range(db, booking, rating):
    rider, driver, ride = booking
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(Review(ride_id=ride.id, rater_id=rider.id, rated_id=driver.user_id, rating=rating))
        db.flush()


def test_duplicate_review_is_rejected(db, booking):
    rider, driver, ride = booking
    db.add(Review(ride_id=ride.id, rater_id=rider.id, rated_id=driver.user_id, rating=4))
    db.flush()
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(Review(ride_id=ride.id, rater_id=rider.id, rated_id=driver.user_id, rating=5))
        db.flush()


def test_self_review_is_rejected(db, booking):
    rider, _, ride = booking
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(Review(ride_id=ride.id, rater_id=rider.id, rated_id=rider.id, rating=5))
        db.flush()


def test_duplicate_payment_for_ride_is_rejected(db, booking):
    ride = booking[2]
    db.add(Payment(ride_id=ride.id, amount=Decimal("149.90")))
    db.flush()
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(Payment(ride_id=ride.id, amount=Decimal("149.90")))
        db.flush()
