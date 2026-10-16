"""Driver availability and nearby request matching using PostgreSQL row locks."""
from datetime import datetime, timedelta, timezone
import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2 import Geography, WKTElement
from pydantic import ValidationError
from sqlalchemy import cast, exists, func, select
from sqlalchemy.exc import IntegrityError

from app.auth import DB, check_origin, get_current_user
from app.config import get_settings
from app.driver_schemas import AvailabilityInput, DriverProfileInput, DriverPublic, NearbyDriver, RideOffer, VehicleInfo
from app.models import Driver, Ride, RideDecline, User
from app.ride_schemas import Coordinate, RidePublic
from app.rides import RiderUser, ride_response

router = APIRouter(prefix="/api", tags=["Drivers and matching"])
ACTIVE_RIDE_STATUSES = ("accepted", "arriving", "in_progress")


def require_driver(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != "driver":
        raise HTTPException(403, "Sign in with a driver account to use the driver dashboard.")
    return user


DriverUser = Annotated[User, Depends(require_driver)]


def geography(point):
    return cast(point, Geography(geometry_type=None))


def active_ride_query(driver_id):
    return select(Ride).where(Ride.driver_id == driver_id, Ride.status.in_(ACTIVE_RIDE_STATUSES))


def location_is_fresh(driver: Driver) -> bool:
    return (driver.status == "active" and driver.current_location is not None
            and driver.location_updated_at is not None
            and driver.location_updated_at >= datetime.now(timezone.utc) - timedelta(seconds=get_settings().driver_location_max_age_seconds))


def driver_profile(driver_id: UUID, db, *, lock=False) -> Driver:
    query = select(Driver).where(Driver.user_id == driver_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    driver = db.scalar(query)
    if driver is None:
        raise HTTPException(404, "Save your vehicle profile first.")
    return driver


def profile_response(driver: Driver, db) -> DriverPublic:
    location = None
    if driver.current_location is not None:
        x, y = db.execute(select(func.ST_X(Driver.current_location), func.ST_Y(Driver.current_location))
                          .where(Driver.user_id == driver.user_id)).one()
        location = Coordinate(latitude=y, longitude=x)
    expires = (driver.location_updated_at + timedelta(seconds=get_settings().driver_location_max_age_seconds)
               if driver.location_updated_at else None)
    return DriverPublic(user_id=driver.user_id, vehicle_info=driver.vehicle_info, verified=driver.verified,
                        status=driver.status, current_location=location, location_updated_at=driver.location_updated_at,
                        location_expires_at=expires,
                        available_for_matching=location_is_fresh(driver) and db.scalar(active_ride_query(driver.user_id)) is None)


@router.get("/drivers/me", response_model=DriverPublic | None)
def get_profile(user: DriverUser, db: DB):
    driver = db.get(Driver, user.id)
    return profile_response(driver, db) if driver else None


@router.put("/drivers/me", response_model=DriverPublic, dependencies=[Depends(check_origin)])
def save_profile(data: DriverProfileInput, user: DriverUser, db: DB):
    # Lock the parent even before the profile exists, serializing concurrent first saves.
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    driver = db.scalar(select(Driver).where(Driver.user_id == user.id).with_for_update())
    vehicle = data.vehicle_info.model_dump()
    if driver is None:
        driver = Driver(user_id=user.id, vehicle_info=vehicle)
        db.add(driver)
    elif driver.vehicle_info != vehicle:
        driver.vehicle_info = vehicle
        driver.verified = False
    db.commit()
    db.refresh(driver)
    return profile_response(driver, db)


@router.post("/drivers/me/availability", response_model=DriverPublic, dependencies=[Depends(check_origin)])
def set_availability(data: AvailabilityInput, user: DriverUser, db: DB):
    driver = driver_profile(user.id, db, lock=True)
    if data.status == "active":
        try:
            VehicleInfo.model_validate(driver.vehicle_info)
        except ValidationError:
            raise HTTPException(409, "Save a complete vehicle profile before going online.") from None
        driver.current_location = WKTElement(f"POINT({data.location.longitude} {data.location.latitude})", srid=4326)
        driver.location_updated_at = datetime.now(timezone.utc)
    else:
        driver.current_location = None
        driver.location_updated_at = None
    driver.status = data.status
    db.commit()
    db.refresh(driver)
    return profile_response(driver, db)


@router.get("/drivers/me/ride", response_model=RidePublic | None)
def current_ride(user: DriverUser, db: DB):
    ride = db.scalar(active_ride_query(user.id))
    return ride_response(ride, db) if ride else None


@router.get("/drivers/me/offers", response_model=list[RideOffer])
def ride_offers(user: DriverUser, db: DB):
    driver = driver_profile(user.id, db)
    if not location_is_fresh(driver) or db.scalar(active_ride_query(user.id)) is not None:
        return []
    driver_point = select(Driver.current_location).where(Driver.user_id == user.id).scalar_subquery()
    distance = func.ST_Distance(geography(Ride.pickup_point), geography(driver_point))
    declined = exists(select(RideDecline.ride_id).where(RideDecline.ride_id == Ride.id, RideDecline.driver_id == user.id))
    rows = db.execute(select(Ride, distance).where(
        Ride.status == "requested", Ride.driver_id.is_(None), ~declined,
        func.ST_DWithin(geography(Ride.pickup_point), geography(driver_point), get_settings().matching_radius_meters),
    ).order_by(distance, Ride.created_at, Ride.id).limit(20)).all()
    return [RideOffer(ride=ride_response(ride, db), pickup_distance_meters=math.ceil(meters)) for ride, meters in rows]


@router.get("/rides/{ride_id}/drivers", response_model=list[NearbyDriver])
def nearby_drivers(ride_id: UUID, user: RiderUser, db: DB):
    ride = db.scalar(select(Ride).where(Ride.id == ride_id, Ride.rider_id == user.id))
    if ride is None:
        raise HTTPException(404, "Ride not found.")
    if ride.status != "requested" or ride.driver_id is not None:
        return []
    pickup = select(Ride.pickup_point).where(Ride.id == ride.id).scalar_subquery()
    distance = func.ST_Distance(geography(Driver.current_location), geography(pickup))
    busy = exists(active_ride_query(Driver.user_id))
    declined = exists(select(RideDecline.ride_id).where(RideDecline.ride_id == ride.id, RideDecline.driver_id == Driver.user_id))
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=get_settings().driver_location_max_age_seconds)
    rows = db.execute(select(Driver, User.name, distance).join(User, User.id == Driver.user_id).where(
        User.role == "driver", Driver.status == "active", Driver.location_updated_at >= cutoff,
        ~busy, ~declined,
        func.ST_DWithin(geography(Driver.current_location), geography(pickup), get_settings().matching_radius_meters),
    ).order_by(distance, Driver.user_id).limit(10)).all()
    return [NearbyDriver(driver_id=driver.user_id, name=name, vehicle_info=driver.vehicle_info,
                         verified=driver.verified, distance_meters=math.ceil(meters)) for driver, name, meters in rows]


def lock_requested_ride(ride_id: UUID, db) -> Ride:
    ride = db.scalar(select(Ride).where(Ride.id == ride_id).with_for_update().execution_options(populate_existing=True))
    if ride is None:
        raise HTTPException(404, "Ride not found.")
    return ride


def ensure_eligible(driver: Driver, ride: Ride, db):
    if not location_is_fresh(driver):
        raise HTTPException(409, "Go online with a fresh location before responding to requests.")
    if ride.status != "requested" or ride.driver_id is not None:
        raise HTTPException(409, "This ride is no longer available.")
    if db.scalar(active_ride_query(driver.user_id)) is not None:
        raise HTTPException(409, "You already have an active ride.")
    in_range = db.scalar(select(func.ST_DWithin(geography(Driver.current_location), geography(Ride.pickup_point),
                                               get_settings().matching_radius_meters))
                         .select_from(Driver).join(Ride, Ride.id == ride.id).where(Driver.user_id == driver.user_id))
    if not in_range:
        raise HTTPException(409, "This pickup is outside your matching radius.")


@router.post("/drivers/me/rides/{ride_id}/accept", response_model=RidePublic, dependencies=[Depends(check_origin)])
def accept_ride(ride_id: UUID, user: DriverUser, db: DB):
    # All availability/accept/decline writes lock driver first, then ride.
    driver = driver_profile(user.id, db, lock=True)
    ride = lock_requested_ride(ride_id, db)
    if ride.driver_id == user.id and ride.status in ACTIVE_RIDE_STATUSES:
        return ride_response(ride, db)
    ensure_eligible(driver, ride, db)
    if db.get(RideDecline, (ride.id, user.id)) is not None:
        raise HTTPException(409, "You already declined this ride.")
    ride.driver_id, ride.status = user.id, "accepted"
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "The ride could not be assigned. Refresh your requests.") from None
    db.refresh(ride)
    return ride_response(ride, db)


@router.post("/drivers/me/rides/{ride_id}/decline", status_code=204, dependencies=[Depends(check_origin)])
def decline_ride(ride_id: UUID, user: DriverUser, db: DB):
    driver = driver_profile(user.id, db, lock=True)
    ride = lock_requested_ride(ride_id, db)
    ensure_eligible(driver, ride, db)
    if db.get(RideDecline, (ride.id, user.id)) is None:
        db.add(RideDecline(ride_id=ride.id, driver_id=user.id))
        db.commit()
