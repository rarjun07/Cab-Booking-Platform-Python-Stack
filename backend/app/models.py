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
        CheckConstraint("wallet_balance >= 0", name="ck_users_wallet_balance"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="rider")
    phone: Mapped[str | None] = mapped_column(String(32), unique=True)
    profile_pic: Mapped[str | None] = mapped_column(String(2048))
    rating_avg: Mapped[Decimal] = mapped_column(Numeric(3, 2), server_default="0")
    wallet_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default="0")
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
    __table_args__ = (CheckConstraint("(payment_id IS NOT NULL AND wallet_topup_id IS NULL) OR (payment_id IS NULL AND wallet_topup_id IS NOT NULL)", name="ck_payment_events_target"),)

    stripe_event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    payment_id: Mapped[UUID | None] = mapped_column(ForeignKey("payments.id", ondelete="RESTRICT"), index=True)
    wallet_topup_id: Mapped[UUID | None] = mapped_column(ForeignKey("wallet_topups.id", ondelete="RESTRICT"), index=True)
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
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReceiptEmail(Base):
    __tablename__ = "receipt_emails"
    __table_args__ = (
        UniqueConstraint("ride_id", "user_id", "document_key", name="uq_receipt_emails_document"),
        CheckConstraint("status IN ('queued', 'sent', 'failed')", name="ck_receipt_emails_status"),
        CheckConstraint("attempts BETWEEN 0 AND 3", name="ck_receipt_emails_attempts"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    ride_id: Mapped[UUID] = mapped_column(ForeignKey("rides.id", ondelete="RESTRICT"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    document_key: Mapped[str] = mapped_column(String(64))
    recipient: Mapped[str] = mapped_column(String(254))
    snapshot: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), server_default="queued")
    attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PromoCode(Base):
    __tablename__ = "promo_codes"
    __table_args__ = (
        UniqueConstraint("code", name="uq_promo_codes_code"),
        CheckConstraint("code ~ '^[A-Z0-9]{3,20}$'", name="ck_promo_codes_code"),
        CheckConstraint("percent_off BETWEEN 1 AND 90", name="ck_promo_codes_percent"),
        CheckConstraint("min_fare >= 0 AND max_discount > 0", name="ck_promo_codes_amounts"),
        CheckConstraint("max_uses > 0 AND per_user_limit > 0 AND per_user_limit <= max_uses", name="ck_promo_codes_limits"),
        CheckConstraint("expires_at > starts_at", name="ck_promo_codes_dates"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(20))
    percent_off: Mapped[int] = mapped_column(SmallInteger)
    min_fare: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    max_discount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    max_uses: Mapped[int] = mapped_column(Integer)
    per_user_limit: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PromoRedemption(Base):
    __tablename__ = "promo_redemptions"
    __table_args__ = (
        CheckConstraint("base_amount > 0 AND discount_amount > 0 AND final_amount >= 50 AND base_amount = discount_amount + final_amount", name="ck_promo_redemptions_amounts"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    promo_id: Mapped[UUID] = mapped_column(ForeignKey("promo_codes.id", ondelete="RESTRICT"), index=True)
    ride_id: Mapped[UUID] = mapped_column(ForeignKey("rides.id", ondelete="RESTRICT"), unique=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    code: Mapped[str] = mapped_column(String(20))
    base_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    final_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WalletTopup(Base):
    __tablename__ = "wallet_topups"
    __table_args__ = (
        UniqueConstraint("user_id", "request_key", name="uq_wallet_topups_request"),
        CheckConstraint("amount BETWEEN 50 AND 10000 AND currency = 'inr'", name="ck_wallet_topups_amount"),
        CheckConstraint("status IN ('pending','processing','succeeded','failed','cancelled')", name="ck_wallet_topups_status"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    request_key: Mapped[UUID] = mapped_column(Uuid)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), server_default="inr")
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    status: Mapped[str] = mapped_column(String(20), server_default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    credited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WalletEntry(Base):
    __tablename__ = "wallet_entries"
    __table_args__ = (
        UniqueConstraint("topup_id", name="uq_wallet_entries_topup"),
        CheckConstraint("amount > 0", name="ck_wallet_entries_amount"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    topup_id: Mapped[UUID] = mapped_column(ForeignKey("wallet_topups.id", ondelete="RESTRICT"))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
