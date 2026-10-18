"""Rider test wallet: balance changes only in a verified, atomic webhook credit."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.auth import DB, check_origin
from app.events import Events
from app.models import PaymentEvent, User, WalletEntry, WalletTopup
from app.payment_gateway import Gateway, payment_settings
from app.payment_schemas import PaymentInput
from app.rides import RiderUser
from app.stripe_validation import canonical_status, checkout_secret, validate_test_intent
from app.wallet_schemas import EntryPublic, TopupInput, TopupIntentPublic, TopupPublic, WalletPublic

router = APIRouter(prefix="/api/wallet", tags=["Test wallet"])


def metadata(topup):
    return {"project": "cab-booking-platform", "kind": "wallet_topup", "wallet_topup_id": str(topup.id), "user_id": str(topup.user_id)}


@router.get("", response_model=WalletPublic)
def wallet(user: RiderUser, db: DB):
    # Hold a short share lock while reading balance/ledger so a concurrent credit
    # cannot commit halfway through this snapshot response. No network work here.
    owner = db.scalar(select(User).where(User.id == user.id).with_for_update(read=True).execution_options(populate_existing=True))
    entries = db.scalars(select(WalletEntry).where(WalletEntry.user_id == user.id)
                         .order_by(WalletEntry.created_at.desc(), WalletEntry.id.desc()).limit(10)).all()
    topups = db.scalars(select(WalletTopup).where(WalletTopup.user_id == user.id)
                        .order_by(WalletTopup.created_at.desc(), WalletTopup.id.desc()).limit(5)).all()
    return WalletPublic(balance=owner.wallet_balance, entries=[EntryPublic.model_validate(e) for e in entries],
                        topups=[TopupPublic.model_validate(t) for t in topups])


def owned_topup(topup_id, user, db, *, lock=False):
    query = select(WalletTopup).where(WalletTopup.id == topup_id, WalletTopup.user_id == user.id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    topup = db.scalar(query)
    if topup is None:
        raise HTTPException(404, "Top-up not found.")
    return topup


@router.get("/topups/{topup_id}", response_model=TopupPublic)
def topup_status(topup_id: UUID, user: RiderUser, db: DB):
    return owned_topup(topup_id, user, db)


def prepare_topup(topup_id, user, db, gateway):
    settings = payment_settings()
    topup = owned_topup(topup_id, user, db, lock=True)
    if topup.status == "cancelled":
        raise HTTPException(409, "This top-up is closed.")
    if topup.stripe_payment_intent_id is None and topup.created_at < datetime.now(timezone.utc) - timedelta(hours=23):
        raise HTTPException(409, "This unlinked top-up needs reconciliation before checkout can be recreated.")
    intent = gateway.retrieve(topup.stripe_payment_intent_id) if topup.stripe_payment_intent_id else gateway.create_topup(topup)
    validate_test_intent(intent, topup.amount, topup.currency, metadata(topup), topup.stripe_payment_intent_id)
    if intent["status"] == "canceled":
        raise HTTPException(409, "This test top-up was cancelled and cannot be reused.")
    secret = checkout_secret(intent, paid=topup.status == "succeeded")
    topup.stripe_payment_intent_id = intent["id"]
    db.commit()
    db.refresh(topup)
    return TopupIntentPublic(topup=TopupPublic.model_validate(topup), publishable_key=settings.stripe_publishable_key,
                             client_secret=secret, stripe_status=intent["status"])


@router.post("/topups", response_model=TopupIntentPublic, dependencies=[Depends(check_origin)])
def create_topup(data: TopupInput, user: RiderUser, db: DB, gateway: Gateway):
    payment_settings()
    # Serialize request-key creation, then release the user before provider I/O.
    db.scalar(select(User).where(User.id == user.id).with_for_update(key_share=True))
    topup = db.scalar(select(WalletTopup).where(WalletTopup.user_id == user.id, WalletTopup.request_key == data.request_key))
    if topup is None:
        topup = WalletTopup(user_id=user.id, request_key=data.request_key, amount=data.amount)
        db.add(topup)
    elif topup.amount != data.amount:
        raise HTTPException(409, "This retry key already belongs to a different top-up amount.")
    db.commit()
    return prepare_topup(topup.id, user, db, gateway)


@router.post("/topups/{topup_id}/payment-intent", response_model=TopupIntentPublic, dependencies=[Depends(check_origin)])
def resume_topup(topup_id: UUID, data: PaymentInput, user: RiderUser, db: DB, gateway: Gateway):
    return prepare_topup(topup_id, user, db, gateway)


def process_topup_webhook(event, intent_id, db, gateway, events):
    topup = db.scalar(select(WalletTopup).where(WalletTopup.stripe_payment_intent_id == intent_id)
                      .with_for_update().execution_options(populate_existing=True))
    if topup is None:
        return {"received": True, "ignored": True}
    recorded = db.get(PaymentEvent, event["id"])
    if recorded:
        if recorded.wallet_topup_id != topup.id:
            raise HTTPException(409, "This event was already recorded for another payment.")
        return {"received": True, "duplicate": True}
    intent = gateway.retrieve(intent_id)
    validate_test_intent(intent, topup.amount, topup.currency, metadata(topup), topup.stripe_payment_intent_id)
    status = canonical_status(intent)
    if topup.status not in ("succeeded", "cancelled"):
        if status == "succeeded":
            owner = db.scalar(select(User).where(User.id == topup.user_id)
                              .with_for_update(key_share=True).execution_options(populate_existing=True))
            if db.scalar(select(WalletEntry.id).where(WalletEntry.topup_id == topup.id)) is not None:
                raise HTTPException(409, "This top-up already has a credit requiring reconciliation.")
            db.add(WalletEntry(user_id=owner.id, topup_id=topup.id, amount=topup.amount))
            owner.wallet_balance += topup.amount
            topup.credited_at = datetime.now(timezone.utc)
        topup.status = status
    db.add(PaymentEvent(stripe_event_id=event["id"], wallet_topup_id=topup.id, event_type=event["type"]))
    db.commit()
    events.wallet_changed(topup.user_id)
    return {"received": True}
