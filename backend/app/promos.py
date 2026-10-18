"""One server-priced promo on a completed trip, before its invoice is created."""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select

from app.auth import DB, check_origin
from app.events import Events
from app.history import completed_ride
from app.models import Payment, PromoCode, PromoRedemption
from app.rides import RiderUser
from app.wallet_schemas import PromoInput, PromoPublic

router = APIRouter(prefix="/api/rides", tags=["Promo codes"])


@router.get("/{ride_id}/promo", response_model=PromoPublic | None)
def applied_promo(ride_id: UUID, user: RiderUser, db: DB):
    ride = completed_ride(ride_id, user, db, purpose="Promo codes")
    return db.scalar(select(PromoRedemption).where(PromoRedemption.ride_id == ride.id))


@router.post("/{ride_id}/promo", response_model=PromoPublic, status_code=201, dependencies=[Depends(check_origin)])
def apply_promo(ride_id: UUID, data: PromoInput, user: RiderUser, db: DB, response: Response, events: Events):
    ride = completed_ride(ride_id, user, db, lock=True, purpose="Promo codes")
    previous = db.scalar(select(PromoRedemption).where(PromoRedemption.ride_id == ride.id))
    if previous:
        if previous.code != data.code:
            raise HTTPException(409, "A promo is already applied to this trip.")
        response.status_code = 200
        return previous
    if db.scalar(select(Payment.id).where(Payment.ride_id == ride.id)) is not None:
        raise HTTPException(409, "Apply a promo before opening checkout; this invoice is already fixed.")
    promo = db.scalar(select(PromoCode).where(PromoCode.code == data.code).with_for_update().execution_options(populate_existing=True))
    now = datetime.now(timezone.utc)
    if promo is None or not promo.active or not (promo.starts_at <= now < promo.expires_at):
        raise HTTPException(422, "This promo code is unavailable or expired.")
    uses = db.scalar(select(func.count()).select_from(PromoRedemption).where(PromoRedemption.promo_id == promo.id))
    personal = db.scalar(select(func.count()).select_from(PromoRedemption).where(PromoRedemption.promo_id == promo.id, PromoRedemption.user_id == user.id))
    if uses >= promo.max_uses or personal >= promo.per_user_limit:
        raise HTTPException(409, "This promo's usage limit has been reached.")
    base = ride.fare_actual if ride.fare_actual is not None else ride.fare_estimate
    if base < promo.min_fare:
        raise HTTPException(422, "This fare is below the promo's minimum fare.")
    # Project policy: retain at least INR 50 after a discount, independently of
    # account-specific provider/settlement-currency minimums.
    discount = min((base * Decimal(promo.percent_off) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                   promo.max_discount, max(base - Decimal("50.00"), Decimal("0.00")))
    if discount <= 0:
        raise HTTPException(422, "This fare is too small for a promo discount.")
    redemption = PromoRedemption(promo_id=promo.id, ride_id=ride.id, user_id=user.id, code=promo.code,
                                 base_amount=base, discount_amount=discount, final_amount=base - discount)
    db.add(redemption)
    ride.fare_actual = redemption.final_amount
    db.commit()
    db.refresh(redemption)
    events.payment_changed(None, ride)
    return redemption
