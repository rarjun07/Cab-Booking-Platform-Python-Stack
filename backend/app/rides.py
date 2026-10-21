"""Authenticated estimates and PostgreSQL ride requests using server-signed quotes."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from geoalchemy2 import WKTElement
import jwt
from jwt import InvalidTokenError
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.auth import DB, ISSUER, check_origin, get_current_user
from app.config import get_settings
from app.models import Ride, User
from app.events import Events
from app.ride_schemas import Coordinate, FareBreakdown, FareEstimate, QuoteContents, RidePublic, RideRequest, RouteMetrics, RoadRoute
from app.routing import OSRMProvider, get_route_provider

router = APIRouter(prefix="/api/rides", tags=["Rides"])
QUOTE_AUDIENCE = "cab-fare-quote"


def require_rider(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != "rider":
        raise HTTPException(403, "Sign in with a rider account to request a ride.")
    return user


RiderUser = Annotated[User, Depends(require_rider)]


def parse_coordinate(value: str) -> Coordinate:
    try:
        latitude, longitude = value.split(",")
        return Coordinate(latitude=float(latitude), longitude=float(longitude))
    except (ValueError, ValidationError):
        raise HTTPException(422, "Use latitude,longitude with latitude -90 to 90 and longitude -180 to 180.") from None


def calculate_fare(metrics: RouteMetrics) -> FareBreakdown:
    settings = get_settings()
    cents = Decimal("0.01")
    def money(value):
        return value.quantize(cents, rounding=ROUND_HALF_UP)
    base = money(settings.fare_base)
    distance = money(Decimal(metrics.distance_meters) / 1000 * settings.fare_per_km)
    duration = money(Decimal(metrics.duration_secs) / 60 * settings.fare_per_minute)
    subtotal = base + distance + duration
    total = money(max(settings.fare_minimum, subtotal))
    return FareBreakdown(base_fare=base, distance_charge=distance, time_charge=duration,
                         minimum_adjustment=total - subtotal, total=total)


@router.get("/estimate", response_model=FareEstimate)
def estimate(origin: str, dest: str, user: RiderUser,
             provider: Annotated[OSRMProvider, Depends(get_route_provider)]):
    pickup, destination = parse_coordinate(origin), parse_coordinate(dest)
    if pickup == destination:
        raise HTTPException(422, "Pickup and destination must be different.")
    metrics = provider.route(pickup, destination)
    breakdown = calculate_fare(metrics)
    contents = QuoteContents(pickup=pickup, destination=destination,
                             distance_meters=metrics.distance_meters, duration_secs=metrics.duration_secs,
                             fare_estimate=breakdown.total)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=get_settings().quote_lifetime_seconds)
    token = jwt.encode({**contents.model_dump(mode="json"), "sub": str(user.id), "jti": str(uuid4()),
                        "iat": now, "exp": expires_at, "iss": ISSUER, "aud": QUOTE_AUDIENCE},
                       get_settings().jwt_secret.get_secret_value(), algorithm="HS256")
    return FareEstimate(**contents.model_dump(), geometry=getattr(metrics, "geometry", None),
                        quote_token=token, expires_at=expires_at, breakdown=breakdown)


@router.get("/{ride_id}/route", response_model=RoadRoute)
def saved_route(ride_id: UUID, user: Annotated[User, Depends(get_current_user)], db: DB,
                provider: Annotated[OSRMProvider, Depends(get_route_provider)]):
    # Authorize before contacting OSRM. Exact saved coordinates are already
    # available to these participants, never to another rider/unassigned driver.
    ride = db.get(Ride, ride_id)
    if ride is None or user.id not in (ride.rider_id, ride.driver_id):
        raise HTTPException(404, "Ride not found.")
    saved = ride_response(ride, db)
    return provider.route(saved.pickup, saved.destination)


def validate_quote(token: str, user: User):
    try:
        claims = jwt.decode(token, get_settings().jwt_secret.get_secret_value(), algorithms=["HS256"],
                            issuer=ISSUER, audience=QUOTE_AUDIENCE,
                            options={"require": ["sub", "jti", "iat", "exp", "iss", "aud"]})
        if claims["sub"] != str(user.id):
            raise HTTPException(403, "This fare quote belongs to another rider.")
        return UUID(claims["jti"]), QuoteContents.model_validate(claims)
    except (InvalidTokenError, ValueError, TypeError, ValidationError):
        raise HTTPException(422, "This fare quote is invalid or expired. Get a new estimate.") from None


def ride_response(ride: Ride, db, *, coordinates=None) -> RidePublic:
    pickup_x, pickup_y, destination_x, destination_y = coordinates if coordinates is not None else db.execute(
        select(func.ST_X(Ride.pickup_point), func.ST_Y(Ride.pickup_point),
               func.ST_X(Ride.drop_point), func.ST_Y(Ride.drop_point)).where(Ride.id == ride.id)
    ).one()
    return RidePublic(id=ride.id, status=ride.status, driver_id=ride.driver_id,
                      pickup=Coordinate(latitude=pickup_y, longitude=pickup_x),
                      destination=Coordinate(latitude=destination_y, longitude=destination_x),
                      fare_estimate=ride.fare_estimate, distance_meters=ride.distance_meters,
                      duration_secs=ride.duration_secs, created_at=ride.created_at)


@router.post("/request", response_model=RidePublic, status_code=201, dependencies=[Depends(check_origin)])
def request_ride(data: RideRequest, response: Response, user: RiderUser, db: DB, events: Events):
    quote_id, contents = validate_quote(data.quote_token, user)
    existing = db.scalar(select(Ride).where(Ride.quote_id == quote_id, Ride.rider_id == user.id))
    if existing:
        response.status_code = 200
        return ride_response(existing, db)
    ride = Ride(rider_id=user.id, quote_id=quote_id,
                pickup_point=WKTElement(f"POINT({contents.pickup.longitude} {contents.pickup.latitude})", srid=4326),
                drop_point=WKTElement(f"POINT({contents.destination.longitude} {contents.destination.latitude})", srid=4326),
                fare_estimate=contents.fare_estimate, distance_meters=contents.distance_meters,
                duration_secs=contents.duration_secs)
    db.add(ride)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        ride = db.scalar(select(Ride).where(Ride.quote_id == quote_id, Ride.rider_id == user.id))
        if ride is None:
            raise HTTPException(409, "The ride could not be saved. Please try again.") from None
        response.status_code = 200
    db.refresh(ride)
    events.ride_changed(ride)
    return ride_response(ride, db)


@router.get("/{ride_id}/status", response_model=RidePublic)
def ride_status(ride_id: UUID, user: RiderUser, db: DB):
    ride = db.scalar(select(Ride).where(Ride.id == ride_id, Ride.rider_id == user.id))
    if ride is None:
        raise HTTPException(404, "Ride not found.")
    return ride_response(ride, db)


@router.get("/current", response_model=RidePublic | None)
def current_ride(user: RiderUser, db: DB):
    ride = db.scalar(select(Ride).where(Ride.rider_id == user.id,
                                       Ride.status.in_(("requested", "accepted", "arriving", "in_progress")))
                     .order_by(Ride.created_at.desc(), Ride.id.desc()).limit(1))
    if ride is None:
        ride = db.scalar(select(Ride).where(Ride.rider_id == user.id, Ride.status == "completed")
                         .order_by(Ride.created_at.desc(), Ride.id.desc()).limit(1))
    return ride_response(ride, db) if ride else None
