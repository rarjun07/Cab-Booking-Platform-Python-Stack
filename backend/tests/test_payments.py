from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import hmac
import json
import time
from uuid import UUID, uuid4
from threading import Barrier

from fastapi import HTTPException
from geoalchemy2 import WKTElement
from pydantic import SecretStr, ValidationError
import pytest
from sqlalchemy import func, select
from sqlalchemy import delete, text
from sqlalchemy.orm import Session
import stripe

from app.config import Settings, get_settings
from app.main import app
from app.models import Payment, PaymentEvent, Ride, User
from app.payment_gateway import get_payment_gateway
from app.payment_gateway import StripeGateway
from app.payments import prepare_payment, process_webhook
from app.payment_schemas import PaymentInput

WEBHOOK_SECRET = "whsec_unit_test_fixture_only"


@pytest.fixture
def gateway(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "stripe_secret_key", SecretStr("sk_test_unit_fixture_only"))
    monkeypatch.setattr(settings, "stripe_publishable_key", "pk_test_unit_fixture_only")
    monkeypatch.setattr(settings, "stripe_webhook_secret", SecretStr(WEBHOOK_SECRET))

    class FakeGateway:
        intent = None
        creates = 0
        retrieves = 0
        unavailable = False

        def create(self, payment, ride):
            if self.unavailable:
                raise HTTPException(503, "Provider unavailable.")
            self.creates += 1
            intent_id = "pi_unit" + uuid4().hex
            self.intent = {"id": intent_id, "object": "payment_intent", "livemode": False,
                           "amount": int(payment.amount * 100), "amount_received": 0, "currency": "inr",
                           "status": "requires_payment_method", "client_secret": intent_id + "_secret_unit",
                           "metadata": {"project": "cab-booking-platform", "payment_id": str(payment.id),
                                        "ride_id": str(ride.id), "rider_id": str(ride.rider_id)}}
            return deepcopy(self.intent)

        def retrieve(self, intent_id):
            if self.unavailable:
                raise HTTPException(503, "Provider unavailable.")
            self.retrieves += 1
            return deepcopy(self.intent)

    fake = FakeGateway()
    app.dependency_overrides[get_payment_gateway] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_payment_gateway, None)


@pytest.fixture
def completed_ride(client, account, db):
    user = client.post("/api/auth/register", json=account)
    assert user.status_code == 201
    ride = Ride(rider_id=UUID(user.json()["id"]), status="completed", fare_estimate=Decimal("104.38"),
                pickup_point=WKTElement("POINT(77.209 28.6139)", srid=4326),
                drop_point=WKTElement("POINT(77.2295 28.6129)", srid=4326))
    db.add(ride)
    db.flush()
    return ride


def checkout(client, ride):
    result = client.post(f"/api/rides/{ride.id}/payment-intent", json={})
    assert result.status_code == 200
    return result.json()


def webhook(client, gateway, *, event_id=None, event_type="payment_intent.succeeded", timestamp=None, changes=None, signature=None):
    event = {"id": event_id or "evt_unit" + uuid4().hex, "object": "event", "livemode": False,
             "type": event_type, "data": {"object": {"id": gateway.intent["id"] if gateway.intent else "pi_foreign"}}}
    if changes:
        event.update(changes)
    body = json.dumps(event, separators=(",", ":")).encode()
    now = int(time.time()) if timestamp is None else timestamp
    digest = hmac.new(WEBHOOK_SECRET.encode(), str(now).encode() + b"." + body, hashlib.sha256).hexdigest()
    return client.post("/api/webhooks/stripe", content=body, headers={"Stripe-Signature": signature or f"t={now},v1={digest}", "Origin": "https://webhook.example"})


def succeed(gateway):
    gateway.intent["status"] = "succeeded"
    gateway.intent["amount_received"] = gateway.intent["amount"]


def test_invoice_uses_stored_fare_and_reuses_payment_intent(client, completed_ride, gateway, db):
    assert client.get(f"/api/rides/{completed_ride.id}/payment").json() is None
    first, second = checkout(client, completed_ride), checkout(client, completed_ride)
    assert first["payment"]["id"] == second["payment"]["id"] and gateway.creates == 1
    assert gateway.intent["amount"] == 10438
    assert db.scalar(select(func.count()).select_from(Payment)) == 1
    assert completed_ride.fare_actual == Decimal("104.38")
    assert first["payment"]["status"] == "pending" and first["payment"]["currency"] == "inr"
    assert first["client_secret"] and first["publishable_key"].startswith("pk_test_")
    assert client.post(f"/api/rides/{completed_ride.id}/payment-intent", json={"amount": 1}).status_code == 422


def test_success_requires_signed_webhook_and_duplicate_does_not_double_apply(client, completed_ride, gateway, db):
    checkout(client, completed_ride)
    succeed(gateway)
    # Provider/browser success alone does not mark the invoice paid.
    assert checkout(client, completed_ride)["client_secret"] is None
    assert db.scalar(select(Payment)).status == "pending"
    event_id = "evt_unit" + uuid4().hex
    assert webhook(client, gateway, event_id=event_id).status_code == 200
    saved = db.scalar(select(Payment))
    paid_at = saved.paid_at
    assert saved.status == "succeeded" and paid_at is not None
    duplicate = webhook(client, gateway, event_id=event_id)
    assert duplicate.status_code == 200 and duplicate.json()["duplicate"]
    assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 1
    assert saved.paid_at == paid_at
    assert client.get(f"/api/rides/{completed_ride.id}/payment").json()["status"] == "succeeded"


@pytest.mark.parametrize("kind", ["missing", "bad", "expired", "tampered", "invalid_json", "oversized"])
def test_webhook_signature_and_body_guards(client, completed_ride, gateway, db, kind):
    checkout(client, completed_ride)
    if kind == "missing":
        response = client.post("/api/webhooks/stripe", content=b"{}")
    elif kind == "bad":
        response = webhook(client, gateway, signature="t=1,v1=bad")
    elif kind == "expired":
        response = webhook(client, gateway, timestamp=int(time.time()) - 600)
    elif kind in ("tampered", "invalid_json"):
        stamp = int(time.time())
        signed = b"{}" if kind == "tampered" else b"invalid-json"
        body = b'{"changed":true}' if kind == "tampered" else signed
        digest = hmac.new(WEBHOOK_SECRET.encode(), str(stamp).encode() + b"." + signed, hashlib.sha256).hexdigest()
        response = client.post("/api/webhooks/stripe", content=body, headers={"Stripe-Signature": f"t={stamp},v1={digest}"})
    else:
        response = client.post("/api/webhooks/stripe", content=b"x" * 262145, headers={"Stripe-Signature": "test"})
    assert response.status_code == (413 if kind == "oversized" else 400)
    assert db.scalar(select(Payment)).status == "pending"
    assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 0


@pytest.mark.parametrize("mismatch", ["amount", "currency", "livemode", "metadata", "id", "amount_received"])
def test_canonical_intent_must_match_invoice(client, completed_ride, gateway, db, mismatch):
    checkout(client, completed_ride)
    succeed(gateway)
    original_id = gateway.intent["id"]
    if mismatch == "amount": gateway.intent["amount"] += 1
    elif mismatch == "currency": gateway.intent["currency"] = "usd"
    elif mismatch == "livemode": gateway.intent["livemode"] = True
    elif mismatch == "metadata": gateway.intent["metadata"]["rider_id"] = str(uuid4())
    elif mismatch == "id": gateway.intent["id"] = "pi_wrong"
    else: gateway.intent["amount_received"] -= 1
    response = webhook(client, gateway, changes={"data": {"object": {"id": original_id}}})
    assert response.status_code == 409
    assert db.scalar(select(Payment)).status == "pending"
    assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 0


def test_out_of_order_events_use_current_state_and_paid_never_regresses(client, completed_ride, gateway, db):
    checkout(client, completed_ride)
    succeed(gateway)
    assert webhook(client, gateway, event_type="payment_intent.payment_failed").status_code == 200
    saved = db.scalar(select(Payment))
    paid_at = saved.paid_at
    assert saved.status == "succeeded"
    gateway.intent.update(status="requires_payment_method", last_payment_error={"code": "card_declined"})
    assert webhook(client, gateway, event_type="payment_intent.payment_failed").status_code == 200
    assert saved.status == "succeeded" and saved.paid_at == paid_at


def test_failed_payment_can_retry_same_intent_then_succeed(client, completed_ride, gateway, db):
    original = checkout(client, completed_ride)
    gateway.intent.update(status="requires_payment_method", last_payment_error={"code": "card_declined"})
    assert webhook(client, gateway, event_type="payment_intent.payment_failed").status_code == 200
    assert db.scalar(select(Payment)).status == "failed"
    assert checkout(client, completed_ride)["payment"]["id"] == original["payment"]["id"]
    assert gateway.creates == 1
    succeed(gateway)
    assert webhook(client, gateway).status_code == 200
    assert db.scalar(select(Payment)).status == "succeeded"


def test_provider_failure_keeps_durable_invoice_for_retry(client, completed_ride, gateway, db):
    gateway.unavailable = True
    assert client.post(f"/api/rides/{completed_ride.id}/payment-intent", json={}).status_code == 503
    saved = db.scalar(select(Payment))
    assert saved is not None and saved.stripe_payment_intent_id is None
    payment_id = saved.id
    gateway.unavailable = False
    assert checkout(client, completed_ride)["payment"]["id"] == str(payment_id)


def test_old_unlinked_invoice_is_not_recreated_after_provider_idempotency_window(client, completed_ride, gateway, db):
    db.add(Payment(ride_id=completed_ride.id, amount=Decimal("104.38"), currency="inr",
                   created_at=datetime.now(timezone.utc) - timedelta(days=2)))
    db.flush()
    assert client.post(f"/api/rides/{completed_ride.id}/payment-intent", json={}).status_code == 409
    assert gateway.creates == 0


@pytest.mark.parametrize("secret", [None, "wrong-checkout-secret"])
def test_invalid_provider_checkout_secret_does_not_render_a_payment_form(client, completed_ride, gateway, secret):
    checkout(client, completed_ride)
    gateway.intent["client_secret"] = secret
    assert client.post(f"/api/rides/{completed_ride.id}/payment-intent", json={}).status_code == 502


def test_noncompleted_unauthorized_and_cross_origin_requests_rejected(client, completed_ride, gateway, db, account):
    path = f"/api/rides/{completed_ride.id}"
    completed_ride.status = "in_progress"
    db.flush()
    assert client.post(f"{path}/payment-intent", json={}).status_code == 409
    completed_ride.status = "completed"
    db.flush()
    assert client.post(f"{path}/payment-intent", json={}, headers={"Origin": "https://untrusted.example"}).status_code == 403
    client.post("/api/auth/logout")
    assert client.get(f"{path}/payment").status_code == 401
    account["email"] = "other-payment@example.com"
    client.post("/api/auth/register", json=account)
    assert client.get(f"{path}/payment").status_code == 404
    assert client.post(f"{path}/payment-intent", json={}).status_code == 404
    client.post("/api/auth/logout")
    account.update(role="driver", email="driver-payment@example.com")
    client.post("/api/auth/register", json=account)
    assert client.get(f"{path}/payment").status_code == 403


def test_unconfigured_payments_are_disabled_without_writing_invoice(client, completed_ride, gateway, db, monkeypatch):
    monkeypatch.setattr(get_settings(), "stripe_secret_key", None)
    assert client.get("/api/payments/config").json() == {"configured": False, "publishable_key": None, "test_mode": True}
    assert client.post(f"/api/rides/{completed_ride.id}/payment-intent", json={}).status_code == 503
    assert db.scalar(select(func.count()).select_from(Payment)) == 0


def test_foreign_unhandled_live_and_malformed_events_are_safe(client, completed_ride, gateway, db):
    checkout(client, completed_ride)
    assert webhook(client, gateway, event_type="customer.created").json()["ignored"]
    assert webhook(client, gateway, changes={"data": {"object": {"id": "pi_foreign"}}}).json()["ignored"]
    assert webhook(client, gateway, changes={"livemode": True}).status_code == 400
    assert webhook(client, gateway, changes={"data": {"object": {"id": {}}}}).status_code == 400
    assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 0


def test_completed_ride_is_recoverable_for_checkout_after_reload(client, completed_ride):
    assert client.get("/api/rides/current").json()["id"] == str(completed_ride.id)


@pytest.mark.parametrize("variable,value", [("stripe_secret_key", "sk_live_forbidden"), ("stripe_publishable_key", "pk_live_forbidden"), ("stripe_webhook_secret", "invalid")])
def test_live_keys_are_rejected_by_configuration(variable, value):
    values = get_settings().model_dump()
    values[variable] = value
    with pytest.raises(ValidationError):
        Settings(**values)


def test_sdk_adapter_uses_real_stripe_objects_and_stable_idempotency_key(completed_ride, gateway, db, monkeypatch):
    calls = []
    payment = Payment(ride_id=completed_ride.id, amount=Decimal("104.38"), currency="inr")
    db.add(payment)
    db.flush()

    class IntentService:
        def create(self, params, options):
            calls.append((params, options))
            return stripe.PaymentIntent.construct_from({"id": "pi_sdkfixture", "metadata": params["metadata"]}, None)

        def retrieve(self, intent_id):
            return stripe.PaymentIntent.construct_from({"id": intent_id}, None)

    from types import SimpleNamespace
    adapter = StripeGateway()
    monkeypatch.setattr(adapter, "client", lambda: SimpleNamespace(v1=SimpleNamespace(payment_intents=IntentService())))
    created = adapter.create(payment, completed_ride)
    assert isinstance(created, dict) and isinstance(created["metadata"], dict)
    assert adapter.retrieve("pi_sdkfixture") == {"id": "pi_sdkfixture"}
    assert calls[0][0]["amount"] == 10438 and calls[0][0]["payment_method_types"] == ["card"]
    assert calls[0][1]["idempotency_key"] == f"cab-booking-payment:{payment.id}"


@pytest.mark.parametrize("scenario", ["create", "webhook"])
def test_concurrent_retries_use_one_invoice_or_recorded_event(test_engine, gateway, notifications, scenario):
    user_id, ride_id = uuid4(), uuid4()
    try:
        with Session(test_engine) as setup:
            user = User(id=user_id, name="Payment concurrency", email=f"{user_id}@example.com", role="rider", password_hash="unused-test-hash")
            setup.add(user)
            setup.flush()
            setup.add(Ride(id=ride_id, rider_id=user_id, status="completed", fare_estimate=Decimal("104.38"),
                           pickup_point=WKTElement("POINT(77.209 28.6139)", srid=4326),
                           drop_point=WKTElement("POINT(77.2295 28.6129)", srid=4326)))
            setup.commit()
            if scenario == "webhook":
                prepare_payment(ride_id, PaymentInput(), setup.get(User, user_id), setup, gateway)
                succeed(gateway)
        event = {"id": "evt_concurrent" + uuid4().hex, "object": "event", "livemode": False,
                 "type": "payment_intent.succeeded", "data": {"object": {"id": gateway.intent["id"] if gateway.intent else "pi_unused"}}}
        payload = json.dumps(event).encode()
        stamp = int(time.time())
        digest = hmac.new(WEBHOOK_SECRET.encode(), str(stamp).encode() + b"." + payload, hashlib.sha256).hexdigest()
        barrier = Barrier(2)

        def attempt(_):
            with Session(test_engine) as db:
                db.execute(text("SET LOCAL lock_timeout = '5s'"))
                user = db.get(User, user_id)
                barrier.wait(timeout=5)
                if scenario == "create":
                    return str(prepare_payment(ride_id, PaymentInput(), user, db, gateway).payment.id)
                return process_webhook(payload, f"t={stamp},v1={digest}", db, gateway, notifications)

        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(attempt, range(2)))
        with Session(test_engine) as check:
            assert check.scalar(select(func.count()).select_from(Payment).where(Payment.ride_id == ride_id)) == 1
            if scenario == "create":
                assert results[0] == results[1] and gateway.creates == 1
            else:
                assert sum(bool(result.get("duplicate")) for result in results) == 1
                assert check.scalar(select(Payment).where(Payment.ride_id == ride_id)).status == "succeeded"
                assert check.scalar(select(func.count()).select_from(PaymentEvent).where(PaymentEvent.stripe_event_id == event["id"])) == 1
    finally:
        with Session(test_engine) as cleanup:
            payment_ids = select(Payment.id).where(Payment.ride_id == ride_id)
            cleanup.execute(delete(PaymentEvent).where(PaymentEvent.payment_id.in_(payment_ids)))
            cleanup.execute(delete(Payment).where(Payment.ride_id == ride_id))
            cleanup.execute(delete(Ride).where(Ride.id == ride_id))
            cleanup.execute(delete(User).where(User.id == user_id))
            cleanup.commit()
