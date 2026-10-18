"""Owner-only test checkout and signed, replay-safe Stripe payment webhooks."""
from datetime import datetime, timedelta, timezone
import re
from uuid import UUID

from anyio import to_thread
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
import stripe

from app.auth import DB, check_origin
from app.config import get_settings
from app.events import Events
from app.models import Payment, PaymentEvent, Ride
from app.payment_gateway import Gateway, payment_settings
from app.payment_schemas import PaymentInput, PaymentIntentPublic, PaymentPublic
from app.rides import RiderUser

router = APIRouter(prefix="/api", tags=["Test payments"])
HANDLED_EVENTS = {"payment_intent.succeeded", "payment_intent.processing", "payment_intent.payment_failed", "payment_intent.canceled"}
MAX_WEBHOOK_BYTES = 262144
INTENT_STATUSES = {"succeeded", "processing", "canceled", "requires_payment_method", "requires_confirmation", "requires_action"}


def owned_ride(ride_id, user, db, *, lock=False):
    query = select(Ride).where(Ride.id == ride_id, Ride.rider_id == user.id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    ride = db.scalar(query)
    if ride is None:
        raise HTTPException(404, "Ride not found.")
    return ride


def validate_intent(intent, payment, ride):
    expected_metadata = {"project": "cab-booking-platform", "payment_id": str(payment.id),
                         "ride_id": str(ride.id), "rider_id": str(ride.rider_id)}
    metadata = intent.get("metadata")
    intent_id = intent.get("id")
    if (intent.get("object") != "payment_intent" or intent.get("livemode") is not False
            or intent.get("status") not in INTENT_STATUSES
            or not isinstance(intent_id, str) or len(intent_id) > 255 or not re.fullmatch(r"pi_[A-Za-z0-9]+", intent_id)
            or intent.get("amount") != int(payment.amount * 100) or intent.get("currency") != payment.currency
            or not isinstance(metadata, dict) or any(metadata.get(key) != value for key, value in expected_metadata.items())
            or (payment.stripe_payment_intent_id and intent["id"] != payment.stripe_payment_intent_id)):
        raise HTTPException(409, "The test payment does not match this ride's invoice.")
    if intent.get("status") == "succeeded" and intent.get("amount_received") != int(payment.amount * 100):
        raise HTTPException(409, "The received test amount does not match the invoice.")


@router.get("/payments/config")
def checkout_config(user: RiderUser):
    settings = get_settings()
    configured = bool(settings.stripe_secret_key and settings.stripe_publishable_key and settings.stripe_webhook_secret)
    return {"configured": configured, "publishable_key": settings.stripe_publishable_key if configured else None, "test_mode": True}


@router.get("/rides/{ride_id}/payment", response_model=PaymentPublic | None)
def payment_status(ride_id: UUID, user: RiderUser, db: DB):
    ride = owned_ride(ride_id, user, db)
    return db.scalar(select(Payment).where(Payment.ride_id == ride.id))


@router.post("/rides/{ride_id}/payment-intent", response_model=PaymentIntentPublic, dependencies=[Depends(check_origin)])
def prepare_payment(ride_id: UUID, data: PaymentInput, user: RiderUser, db: DB, gateway: Gateway):
    settings = payment_settings()
    ride = owned_ride(ride_id, user, db, lock=True)
    if ride.status != "completed":
        raise HTTPException(409, "Complete the trip before paying its fare.")
    payment = db.scalar(select(Payment).where(Payment.ride_id == ride.id))
    if payment is None:
        amount = ride.fare_actual if ride.fare_actual is not None else ride.fare_estimate
        if amount <= 0 or amount * 100 > 99999999:
            raise HTTPException(422, "This fare is outside the supported test-payment range.")
        payment = Payment(ride_id=ride.id, amount=amount, currency="inr")
        db.add(payment)
        # Freeze this demo's final invoice from its stored fare, never from client input.
        ride.fare_actual = amount
    db.commit()
    # Durable payment UUID survives provider timeouts and supplies a stable idempotency key.
    payment = db.scalar(select(Payment).where(Payment.ride_id == ride.id).with_for_update().execution_options(populate_existing=True))
    if payment.status in ("cancelled", "refunded"):
        raise HTTPException(409, "This payment is closed and cannot be submitted again.")
    if payment.stripe_payment_intent_id is None and payment.created_at < datetime.now(timezone.utc) - timedelta(hours=23):
        raise HTTPException(409, "This unlinked payment needs reconciliation before another checkout can be created.")
    intent = gateway.retrieve(payment.stripe_payment_intent_id) if payment.stripe_payment_intent_id else gateway.create(payment, ride)
    validate_intent(intent, payment, ride)
    if intent.get("status") == "canceled":
        raise HTTPException(409, "This test payment was cancelled and cannot be reused.")
    payment.stripe_payment_intent_id = intent["id"]
    db.commit()
    db.refresh(payment)
    client_secret = intent.get("client_secret") if intent.get("status") not in ("succeeded", "processing") and payment.status != "succeeded" else None
    requires_form = intent["status"] not in ("succeeded", "processing") and payment.status != "succeeded"
    if requires_form and (not isinstance(client_secret, str) or not client_secret.startswith(f'{intent["id"]}_secret_')):
        raise HTTPException(502, "The payment service returned an invalid checkout.")
    return PaymentIntentPublic(payment=PaymentPublic.model_validate(payment), publishable_key=settings.stripe_publishable_key,
                               client_secret=client_secret, stripe_status=intent["status"])


def process_webhook(payload, signature, db, gateway, events):
    settings = payment_settings()
    try:
        event = stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret.get_secret_value(), tolerance=300).to_dict()
    except (ValueError, stripe.SignatureVerificationError, TypeError, KeyError, AttributeError):
        raise HTTPException(400, "Invalid Stripe webhook signature or payload.") from None
    if event.get("livemode") is not False or event.get("account"):
        raise HTTPException(400, "Only this project's test-mode Stripe events are accepted.")
    if not isinstance(event.get("id"), str) or len(event["id"]) > 255 or not re.fullmatch(r"evt_[A-Za-z0-9]+", event["id"]):
        raise HTTPException(400, "Invalid Stripe event ID.")
    if event.get("type") not in HANDLED_EVENTS:
        return {"received": True, "ignored": True}
    try:
        intent_id = event["data"]["object"]["id"]
    except (KeyError, TypeError):
        raise HTTPException(400, "Invalid payment event.") from None
    if not isinstance(intent_id, str) or len(intent_id) > 255 or not re.fullmatch(r"pi_[A-Za-z0-9]+", intent_id):
        raise HTTPException(400, "Invalid PaymentIntent ID.")
    payment = db.scalar(select(Payment).where(Payment.stripe_payment_intent_id == intent_id)
                        .with_for_update().execution_options(populate_existing=True))
    if payment is None:
        return {"received": True, "ignored": True}
    recorded = db.get(PaymentEvent, event["id"])
    if recorded:
        if recorded.payment_id != payment.id:
            raise HTTPException(409, "This event was already recorded for another payment.")
        return {"received": True, "duplicate": True}
    ride = db.get(Ride, payment.ride_id)
    # Fetch canonical state under the payment lock: deliveries can arrive out of order.
    intent = gateway.retrieve(intent_id)
    validate_intent(intent, payment, ride)
    statuses = {"succeeded": "succeeded", "processing": "processing", "canceled": "cancelled",
                "requires_payment_method": "failed" if intent.get("last_payment_error") else "pending",
                "requires_confirmation": "pending", "requires_action": "pending"}
    status = statuses.get(intent.get("status"))
    if status is None:
        raise HTTPException(409, "Unsupported Stripe payment state.")
    if payment.status not in ("succeeded", "refunded", "cancelled"):
        payment.status = status
        if status == "succeeded":
            payment.paid_at = datetime.now(timezone.utc)
    db.add(PaymentEvent(stripe_event_id=event["id"], payment_id=payment.id, event_type=event["type"]))
    db.commit()
    events.payment_changed(payment, ride)
    return {"received": True}


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: DB, gateway: Gateway, events: Events):
    signature = request.headers.get("stripe-signature", "")
    if not signature or len(signature) > 4096:
        raise HTTPException(400, "Missing or invalid Stripe signature.")
    payload = bytearray()
    async for chunk in request.stream():
        payload.extend(chunk)
        if len(payload) > MAX_WEBHOOK_BYTES:
            raise HTTPException(413, "Webhook body is too large.")
    return await to_thread.run_sync(process_webhook, bytes(payload), signature, db, gateway, events)
