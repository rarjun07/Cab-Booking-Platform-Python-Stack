"""PostgreSQL models for authentication and the cab booking domain."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from geoalchemy2 import Geography, Geometry, WKBElement
from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric,
    SmallInteger, String, Text, UniqueConstraint, Uuid, cast, func, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('rider', 'driver')", name="valid_user_role"),
        CheckConstraint("rating_avg BETWEEN 0 AND 5", name="ck_users_rating_avg"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="rider")
    phone: Mapped[str | None] = mapped_column(String(32), unique=True)
    profile_pic: Mapped[str | None] = mapped_column(String(2048))
    rating_avg: Mapped[Decimal] = mapped_column(Numeric(3, 2), server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class Driver(Base):
    __tablename__ = "drivers"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'offline')", name="ck_drivers_status"),
        CheckConstraint("current_location IS NULL OR (ST_X(current_location) BETWEEN -180 AND 180 AND ST_Y(current_location) BETWEEN -90 AND 90)", name="ck_drivers_coordinates"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    vehicle_info: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    verified: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    current_location: Mapped[WKBElement | None] = mapped_column(Geometry("POINT", srid=4326, spatial_index=True))
    location_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), server_default="offline")


class Ride(Base):
    __tablename__ = "rides"
    __table_args__ = (
        CheckConstraint("status IN ('requested', 'accepted', 'arriving', 'in_progress', 'completed', 'cancelled')", name="ck_rides_status"),
        CheckConstraint("fare_estimate >= 0 AND (fare_actual IS NULL OR fare_actual >= 0)", name="ck_rides_fares"),
        CheckConstraint("distance_meters IS NULL OR distance_meters >= 0", name="ck_rides_distance"),
        CheckConstraint("duration_secs IS NULL OR duration_secs >= 0", name="ck_rides_duration"),
        CheckConstraint("driver_id IS NULL OR rider_id <> driver_id", name="ck_rides_distinct_participants"),
        CheckConstraint("ST_X(pickup_point) BETWEEN -180 AND 180 AND ST_Y(pickup_point) BETWEEN -90 AND 90 AND ST_X(drop_point) BETWEEN -180 AND 180 AND ST_Y(drop_point) BETWEEN -90 AND 90", name="ck_rides_coordinates"),
        Index("ix_rides_rider_created", "rider_id", "created_at"),
        Index("uq_rides_active_driver", "driver_id", unique=True,
              postgresql_where=text("driver_id IS NOT NULL AND status IN ('accepted', 'arriving', 'in_progress')")),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    rider_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    quote_id: Mapped[UUID | None] = mapped_column(Uuid, unique=True)
    driver_id: Mapped[UUID | None] = mapped_column(ForeignKey("drivers.user_id", ondelete="SET NULL"), index=True)
    pickup_point: Mapped[WKBElement] = mapped_column(Geometry("POINT", srid=4326, spatial_index=True))
    drop_point: Mapped[WKBElement] = mapped_column(Geometry("POINT", srid=4326, spatial_index=True))
    status: Mapped[str] = mapped_column(String(20), server_default="requested")
    fare_estimate: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    fare_actual: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    distance_meters: Mapped[int | None] = mapped_column(Integer)
    duration_secs: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# Meter-based radius queries cast WGS84 points to geography; index the same expression.
Index("ix_drivers_location_geography", cast(Driver.current_location, Geography(geometry_type=None)), postgresql_using="gist")
Index("ix_rides_pickup_geography", cast(Ride.pickup_point, Geography(geometry_type=None)), postgresql_using="gist")


class RideDecline(Base):
    __tablename__ = "ride_declines"

    ride_id: Mapped[UUID] = mapped_column(ForeignKey("rides.id", ondelete="CASCADE"), primary_key=True)
    driver_id: Mapped[UUID] = mapped_column(ForeignKey("drivers.user_id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_payments_amount"),
        CheckConstraint("status IN ('pending', 'processing', 'succeeded', 'failed', 'cancelled', 'refunded')", name="ck_payments_status"),
        CheckConstraint("currency = 'inr'", name="ck_payments_currency"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    ride_id: Mapped[UUID] = mapped_column(ForeignKey("rides.id", ondelete="RESTRICT"), unique=True)
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), server_default="inr")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), server_default="pending")


class PaymentEvent(Base):
    __tablename__ = "payment_events"

    stripe_event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    payment_id: Mapped[UUID] = mapped_column(ForeignKey("payments.id", ondelete="RESTRICT"), index=True)
    event_type: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating"),
        CheckConstraint("rater_id <> rated_id", name="ck_reviews_distinct_users"),
        CheckConstraint("comment IS NULL OR length(comment) <= 2000", name="ck_reviews_comment_length"),
        UniqueConstraint("ride_id", "rater_id", name="uq_reviews_ride_rater"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    ride_id: Mapped[UUID] = mapped_column(ForeignKey("rides.id", ondelete="RESTRICT"))
    rater_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    rated_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    rating: Mapped[int] = mapped_column(SmallInteger)
    comment: Mapped[str | None] = mapped_column(Text)
