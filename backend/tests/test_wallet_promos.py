from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import hmac
import io
import json
import time
from threading import Barrier
from uuid import UUID, uuid4

from fastapi import HTTPException, Response
from geoalchemy2 import WKTElement
from pydantic import SecretStr
from pypdf import PdfReader
import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.main import app
from app.models import Payment, PaymentEvent, PromoCode, PromoRedemption, Ride, User, WalletEntry, WalletTopup
from app.payment_gateway import get_payment_gateway, StripeGateway
from app.payment_schemas import PaymentInput
from app.payments import prepare_payment, process_webhook
from app.promos import apply_promo
from app.receipts import receipt_snapshot
from app.wallet import create_topup
from app.wallet_schemas import PromoInput, TopupInput

SIGNING_SECRET = "whsec_wallet_local_fixture_only"


class TestProvider:
    __test__ = False

    def __init__(self):
        self.intents = {}
        self.keys = {}
        self.unavailable = False

    def make(self, key, amount, metadata):
        if self.unavailable:
            raise HTTPException(503, "Controlled test provider unavailable.")
        if key not in self.keys:
            intent_id = "pi_walletfixture" + uuid4().hex
            self.keys[key] = intent_id
            self.intents[intent_id] = {"id": intent_id, "object": "payment_intent", "livemode": False,
                "status": "requires_payment_method", "amount": int(amount * 100), "amount_received": 0,
                "currency": "inr", "metadata": metadata, "client_secret": intent_id + "_secret_fixture"}
        return deepcopy(self.intents[self.keys[key]])

    def create_topup(self, topup):
        return self.make(str(topup.id), topup.amount, {"project": "cab-booking-platform", "kind": "wallet_topup",
                         "wallet_topup_id": str(topup.id), "user_id": str(topup.user_id)})

    def create(self, payment, ride):
        return self.make(str(payment.id), payment.amount, {"project": "cab-booking-platform", "payment_id": str(payment.id),
                         "ride_id": str(ride.id), "rider_id": str(ride.rider_id)})

    def retrieve(self, intent_id):
        if self.unavailable:
            raise HTTPException(503, "Controlled test provider unavailable.")
        return deepcopy(self.intents[intent_id])


@pytest.fixture
def rider(client, account):
    result = client.post("/api/auth/register", json=account)
    assert result.status_code == 201
    return UUID(result.json()["id"])


@pytest.fixture
def provider(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "stripe_secret_key", SecretStr("sk_test_wallet_fixture_only"))
    monkeypatch.setattr(settings, "stripe_publishable_key", "pk_test_wallet_fixture_only")
    monkeypatch.setattr(settings, "stripe_webhook_secret", SecretStr(SIGNING_SECRET))
    fake = TestProvider()
    app.dependency_overrides[get_payment_gateway] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_payment_gateway, None)


def completed(db, rider_id, amount="104.38"):
    ride = Ride(rider_id=rider_id, status="completed", fare_estimate=Decimal(amount),
                pickup_point=WKTElement("POINT(77.209 28.6139)", srid=4326),
                drop_point=WKTElement("POINT(77.2295 28.6129)", srid=4326))
    db.add(ride)
    db.flush()
    return ride


@pytest.fixture
def campaign(db):
    now = datetime.now(timezone.utc)
    promo = PromoCode(code="TEST10", percent_off=10, min_fare=Decimal("80.00"), max_discount=Decimal("50.00"),
                      max_uses=100, per_user_limit=1, starts_at=now-timedelta(hours=1), expires_at=now+timedelta(days=1))
    db.add(promo)
    db.flush()
    return promo


def topup(client, amount="100.00", key=None):
    response = client.post("/api/wallet/topups", json={"amount": amount, "request_key": str(key or uuid4())})
    assert response.status_code == 200
    return response.json()


def signed_event(intent_id, event_id=None, event_type="payment_intent.succeeded"):
    event = {"id": event_id or "evt_walletfixture"+uuid4().hex, "object": "event", "livemode": False,
             "type": event_type, "data": {"object": {"id": intent_id}}}
    body = json.dumps(event).encode()
    stamp = int(time.time())
    digest = hmac.new(SIGNING_SECRET.encode(), str(stamp).encode()+b"."+body, hashlib.sha256).hexdigest()
    return body, f"t={stamp},v1={digest}"


def notify(client, intent_id, **kwargs):
    body, signature = signed_event(intent_id, **kwargs)
    return client.post("/api/webhooks/stripe", content=body, headers={"Stripe-Signature": signature})


def success(provider, intent_id):
    provider.intents[intent_id].update(status="succeeded", amount_received=provider.intents[intent_id]["amount"])


def test_promo_is_server_priced_frozen_and_used_by_stripe_and_pdf(client, rider, db, campaign, provider):
    ride = completed(db, rider)
    path = f"/api/rides/{ride.id}/promo"
    assert client.get(path).json() is None
    result = client.post(path, json={"code": " test10 "})
    assert result.status_code == 201
    assert result.json() == {"code": "TEST10", "base_amount": "104.38", "discount_amount": "10.44", "final_amount": "93.94"}
    assert client.post(path, json={"code": "TEST10"}).status_code == 200
    assert client.post(path, json={"code": "OTHER"}).status_code == 409
    checkout = client.post(f"/api/rides/{ride.id}/payment-intent", json={})
    assert checkout.status_code == 200 and checkout.json()["payment"]["amount"] == "93.94"
    assert list(provider.intents.values())[0]["amount"] == 9394
    assert client.post(path, json={"code": "TEST10"}).status_code == 200
    pdf = client.get(f"/api/rides/{ride.id}/receipt.pdf")
    reader = PdfReader(io.BytesIO(pdf.content))
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    assert all(value in text for value in ("TEST10", "104.38", "10.44", "93.94"))
    assert "not proof of payment" in text
    assert db.scalar(select(func.count()).select_from(PromoRedemption)) == 1


@pytest.mark.parametrize("rule", ["inactive", "expired", "not_started", "minimum", "global_limit", "personal_limit", "invoice"])
def test_promo_rechecks_rules_and_never_changes_an_existing_invoice(client, rider, db, campaign, rule):
    ride = completed(db, rider)
    if rule == "inactive": campaign.active = False
    if rule == "expired": campaign.expires_at = datetime.now(timezone.utc)-timedelta(minutes=1)
    if rule == "not_started": campaign.starts_at = datetime.now(timezone.utc)+timedelta(hours=1)
    if rule == "minimum": campaign.min_fare = Decimal("200.00")
    if rule in ("global_limit", "personal_limit"):
        other = completed(db, rider)
        assert client.post(f"/api/rides/{other.id}/promo", json={"code": campaign.code}).status_code == 201
        if rule == "global_limit": campaign.max_uses = 1
    if rule == "invoice": db.add(Payment(ride_id=ride.id, amount=ride.fare_estimate))
    db.flush()
    response = client.post(f"/api/rides/{ride.id}/promo", json={"code": campaign.code})
    assert response.status_code in (409, 422) and ride.fare_actual is None


def test_promo_discount_cap_floor_role_origin_and_ownership(client, rider, db, campaign, account):
    large = completed(db, rider, "1000.00")
    assert client.post(f"/api/rides/{large.id}/promo", json={"code": campaign.code}).json()["discount_amount"] == "50.00"
    campaign.per_user_limit = 10
    campaign.percent_off = 90
    small = completed(db, rider, "80.00")
    db.flush()
    assert client.post(f"/api/rides/{small.id}/promo", json={"code": campaign.code}).json()["final_amount"] == "50.00"
    fresh = completed(db, rider)
    path = f"/api/rides/{fresh.id}/promo"
    assert client.post(path, json={"code": campaign.code, "discount": "100"}).status_code == 422
    assert client.post(path, json={"code": "A\x00B"}).status_code == 422
    assert client.post(path, json={"code": campaign.code}, headers={"Origin": "https://untrusted.example"}).status_code == 403
    fresh.status = "in_progress"
    db.flush()
    assert client.post(path, json={"code": campaign.code}).status_code == 409
    client.post("/api/auth/logout")
    assert client.get(path).status_code == 401
    client.post("/api/auth/register", json={**account, "email": "other-promo@example.com"})
    assert client.get(path).status_code == 404
    client.post("/api/auth/logout")
    client.post("/api/auth/register", json={**account, "email": "driver-promo@example.com", "role": "driver"})
    assert client.post(path, json={"code": campaign.code}).status_code == 403


def test_wallet_starts_zero_and_topup_retries_do_not_credit_without_webhook(client, rider, db, provider):
    assert client.get("/api/wallet").json() == {"balance": "0.00", "currency": "inr", "entries": [], "topups": []}
    key = uuid4()
    first = topup(client, key=key)
    second = topup(client, key=key)
    assert first["topup"]["id"] == second["topup"]["id"] and len(provider.intents) == 1
    assert first["client_secret"]
    assert client.post("/api/wallet/topups", json={"amount": "200.00", "request_key": str(key)}).status_code == 409
    intent_id = next(iter(provider.intents))
    success(provider, intent_id)
    pending = client.post(f'/api/wallet/topups/{first["topup"]["id"]}/payment-intent', json={})
    assert pending.status_code == 200 and pending.json()["client_secret"] is None
    result = client.get("/api/wallet")
    assert result.json()["balance"] == "0.00" and result.json()["entries"] == []
    assert "client_secret" not in result.text and "stripe_payment_intent_id" not in result.text
    assert result.headers["cache-control"] == "no-store"
    assert db.scalar(select(func.count()).select_from(WalletTopup)) == 1


def test_signed_topup_credits_once_across_replays_and_distinct_events(client, rider, db, provider):
    saved = topup(client)
    intent_id = next(iter(provider.intents))
    success(provider, intent_id)
    event_id = "evt_once"+uuid4().hex
    assert notify(client, intent_id, event_id=event_id).status_code == 200
    credited_at = client.get(f'/api/wallet/topups/{saved["topup"]["id"]}').json()["credited_at"]
    assert notify(client, intent_id, event_id=event_id).json()["duplicate"] is True
    assert notify(client, intent_id).status_code == 200
    state = client.get("/api/wallet").json()
    assert state["balance"] == "100.00" and len(state["entries"]) == 1
    assert state["topups"][0]["credited_at"] == credited_at
    assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 2
    assert db.scalar(select(func.count()).select_from(WalletEntry)) == 1


@pytest.mark.parametrize("mismatch", ["amount", "currency", "user", "topup", "kind", "project", "received", "live", "id"])
def test_wallet_canonical_checks_reject_wrong_intent_without_credit(client, rider, db, provider, mismatch):
    topup(client)
    intent_id = next(iter(provider.intents))
    success(provider, intent_id)
    intent = provider.intents[intent_id]
    if mismatch == "amount": intent["amount"] += 1
    if mismatch == "currency": intent["currency"] = "usd"
    if mismatch == "received": intent["amount_received"] -= 1
    if mismatch == "live": intent["livemode"] = True
    if mismatch == "id": intent["id"] = "pi_other"
    keys = {"user": "user_id", "topup": "wallet_topup_id", "kind": "kind", "project": "project"}
    if mismatch in keys: intent["metadata"][keys[mismatch]] = "wrong"
    assert notify(client, intent_id).status_code == 409
    assert client.get("/api/wallet").json()["balance"] == "0.00"
    assert db.scalar(select(func.count()).select_from(WalletEntry)) == 0
    assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 0


def test_wallet_uses_canonical_state_and_never_regresses_paid_credit(client, rider, db, provider):
    topup(client)
    intent_id = next(iter(provider.intents))
    provider.intents[intent_id]["status"] = "processing"
    assert notify(client, intent_id).status_code == 200
    assert client.get("/api/wallet").json()["balance"] == "0.00"
    success(provider, intent_id)
    assert notify(client, intent_id, event_type="payment_intent.payment_failed").status_code == 200
    provider.intents[intent_id].update(status="requires_payment_method", last_payment_error={"code": "declined"})
    assert notify(client, intent_id).status_code == 200
    state = client.get("/api/wallet").json()
    assert state["balance"] == "100.00" and state["topups"][0]["status"] == "succeeded"
    assert len(state["entries"]) == 1


@pytest.mark.parametrize("amount", ["49.99", "10000.01", "100.001", "NaN", "Infinity", True, 0])
def test_wallet_validates_amount_before_writes(client, rider, db, provider, amount):
    assert client.post("/api/wallet/topups", json={"amount": amount, "request_key": str(uuid4())}).status_code == 422
    assert db.scalar(select(func.count()).select_from(WalletTopup)) == 0


def test_wallet_session_role_owner_origin_and_missing_configuration(client, rider, db, provider, account, monkeypatch):
    saved = topup(client)
    path = f'/api/wallet/topups/{saved["topup"]["id"]}'
    assert client.post(path+"/payment-intent", json={}, headers={"Origin": "https://untrusted.example"}).status_code == 403
    assert client.post("/api/wallet/topups", json={"amount": "100", "request_key": str(uuid4()), "user_id": str(uuid4())}).status_code == 422
    client.post("/api/auth/logout")
    assert client.get("/api/wallet").status_code == 401
    assert client.post(path+"/payment-intent", json={}).status_code == 401
    client.post("/api/auth/register", json={**account, "email": "wallet-outsider@example.com"})
    assert client.get(path).status_code == 404
    assert client.post(path+"/payment-intent", json={}).status_code == 404
    assert client.get("/api/wallet").json()["topups"] == []
    monkeypatch.setattr(get_settings(), "stripe_secret_key", None)
    result = client.post("/api/wallet/topups", json={"amount": "100", "request_key": str(uuid4())})
    assert result.status_code == 503 and db.scalar(select(func.count()).select_from(WalletTopup)) == 1
    client.post("/api/auth/logout")
    client.post("/api/auth/register", json={**account, "email": "wallet-driver@example.com", "role": "driver"})
    assert client.get("/api/wallet").status_code == 403


def test_wallet_provider_failure_keeps_durable_request_and_old_unlinked_request_is_guarded(client, rider, db, provider):
    key = uuid4()
    provider.unavailable = True
    response = client.post("/api/wallet/topups", json={"amount": "100", "request_key": str(key)})
    assert response.status_code == 503
    stored = db.scalar(select(WalletTopup))
    original_id = stored.id
    provider.unavailable = False
    assert topup(client, key=key)["topup"]["id"] == str(original_id)
    older = WalletTopup(user_id=rider, request_key=uuid4(), amount=Decimal("100.00"),
                        created_at=datetime.now(timezone.utc)-timedelta(hours=24))
    db.add(older)
    db.flush()
    assert client.post(f"/api/wallet/topups/{older.id}/payment-intent", json={}).status_code == 409


@pytest.mark.parametrize("first", ["ride", "wallet"])
def test_global_event_id_cannot_credit_another_payment_kind(client, rider, db, provider, first):
    ride = completed(db, rider)
    assert client.post(f"/api/rides/{ride.id}/payment-intent", json={}).status_code == 200
    topup(client)
    ids = {"wallet" if intent["metadata"].get("kind") else "ride": key for key, intent in provider.intents.items()}
    for intent_id in ids.values(): success(provider, intent_id)
    event_id = "evt_shared"+uuid4().hex
    assert notify(client, ids[first], event_id=event_id).status_code == 200
    assert notify(client, ids["wallet" if first == "ride" else "ride"], event_id=event_id).status_code == 409
    assert client.get("/api/wallet").json()["balance"] == ("100.00" if first == "wallet" else "0.00")
    assert db.scalar(select(Payment).where(Payment.ride_id == ride.id)).status == ("pending" if first == "wallet" else "succeeded")
    assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 1


def test_wallet_sdk_adapter_sends_test_metadata_and_stable_idempotency(rider, db, provider, monkeypatch):
    import stripe
    from types import SimpleNamespace
    record = WalletTopup(user_id=rider, request_key=uuid4(), amount=Decimal("100.00"))
    db.add(record)
    db.flush()
    calls = []
    class Service:
        def create(self, params, options):
            calls.append((params, options))
            return stripe.PaymentIntent.construct_from({"id": "pi_adapter", **params}, None)
    adapter = StripeGateway()
    monkeypatch.setattr(adapter, "client", lambda: SimpleNamespace(v1=SimpleNamespace(payment_intents=Service())))
    result = adapter.create_topup(record)
    assert isinstance(result, dict) and calls[0][0]["amount"] == 10000
    assert calls[0][0]["metadata"]["kind"] == "wallet_topup"
    assert calls[0][1]["idempotency_key"] == f"cab-booking-wallet:{record.id}"


@pytest.mark.parametrize("target", ["none", "both"])
def test_event_audit_requires_exactly_one_payment_target(client, rider, db, provider, target):
    topup_id = UUID(topup(client)["topup"]["id"])
    ride = completed(db, rider)
    payment = Payment(ride_id=ride.id, amount=ride.fare_estimate)
    db.add(payment)
    db.flush()
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(PaymentEvent(stripe_event_id="evt_bad"+uuid4().hex, event_type="payment_intent.succeeded",
                            payment_id=payment.id if target == "both" else None,
                            wallet_topup_id=topup_id if target == "both" else None))
        db.flush()


def test_receipt_refreshes_fare_with_discount_committed_after_ride_was_loaded(test_engine, notifications):
    user_id, promo_id, ride_id = uuid4(), uuid4(), None
    try:
        with Session(test_engine) as writer:
            writer.add(User(id=user_id, name="Receipt race", email=f"{user_id}@example.com", role="rider", password_hash="unused"))
            writer.flush()
            ride_id = completed(writer, user_id).id
            code = "PDF"+uuid4().hex[:12].upper()
            now = datetime.now(timezone.utc)
            writer.add(PromoCode(id=promo_id, code=code, percent_off=10, min_fare=Decimal("80"), max_discount=Decimal("50"),
                                 max_uses=100, per_user_limit=1, starts_at=now-timedelta(hours=1), expires_at=now+timedelta(hours=1)))
            writer.commit()
            with Session(test_engine) as reader:
                stale_ride = reader.get(Ride, ride_id)
                assert stale_ride.fare_actual is None
                apply_promo(ride_id, PromoInput(code=code), writer.get(User, user_id), writer, Response(), notifications)
                snapshot = receipt_snapshot(stale_ride, reader)
                assert snapshot["base_amount"] == "104.38"
                assert snapshot["discount_amount"] == "10.44"
                assert snapshot["amount"] == "93.94" and snapshot["amount_label"] == "Final fare"
    finally:
        with Session(test_engine) as cleanup:
            cleanup.execute(delete(PromoRedemption).where(PromoRedemption.promo_id == promo_id))
            cleanup.execute(delete(PromoCode).where(PromoCode.id == promo_id))
            cleanup.execute(delete(Ride).where(Ride.id == ride_id))
            cleanup.execute(delete(User).where(User.id == user_id))
            cleanup.commit()


@pytest.mark.parametrize("scenario", ["creation_retry", "duplicate_event", "different_events", "different_topups"])
def test_concurrent_wallet_requests_and_credits_are_atomic(test_engine, provider, notifications, monkeypatch, scenario):
    user_id, key = uuid4(), uuid4()
    try:
        with Session(test_engine) as setup:
            setup.add(User(id=user_id, name="Wallet concurrency", email=f"{user_id}@example.com", role="rider", password_hash="unused"))
            setup.commit()
            ids = []
            if scenario != "creation_retry":
                first = create_topup(TopupInput(amount="100", request_key=key), setup.get(User, user_id), setup, provider)
                ids.append(provider.keys[str(first.topup.id)])
                if scenario == "different_topups":
                    second = create_topup(TopupInput(amount="200", request_key=uuid4()), setup.get(User, user_id), setup, provider)
                    ids.append(provider.keys[str(second.topup.id)])
                else: ids.append(ids[0])
                for intent_id in ids: success(provider, intent_id)
        if scenario == "different_topups":
            read_barrier = Barrier(2)
            original = provider.retrieve
            def overlapping(intent_id):
                intent = original(intent_id)
                read_barrier.wait(timeout=5)
                return intent
            monkeypatch.setattr(provider, "retrieve", overlapping)
        shared_event = "evt_concurrent"+uuid4().hex
        barrier = Barrier(2)
        def attempt(index):
            with Session(test_engine) as db:
                db.execute(text("SET LOCAL lock_timeout = '5s'"))
                user = db.get(User, user_id)  # Preload balance to test stale-cache refresh.
                barrier.wait(timeout=5)
                if scenario == "creation_retry":
                    return str(create_topup(TopupInput(amount="100", request_key=key), user, db, provider).topup.id)
                body, signature = signed_event(ids[index], event_id=shared_event if scenario == "duplicate_event" else None)
                return process_webhook(body, signature, db, provider, notifications)
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(attempt, range(2)))
        with Session(test_engine) as check:
            entries = check.scalars(select(WalletEntry).where(WalletEntry.user_id == user_id)).all()
            balance = check.get(User, user_id).wallet_balance
            if scenario == "creation_retry":
                assert results[0] == results[1] and len(provider.intents) == 1
                assert balance == 0 and entries == []
            else:
                assert balance == (Decimal("300.00") if scenario == "different_topups" else Decimal("100.00"))
                assert sum(entry.amount for entry in entries) == balance
                assert len(entries) == (2 if scenario == "different_topups" else 1)
                if scenario == "duplicate_event": assert sum(bool(r.get("duplicate")) for r in results) == 1
    finally:
        with Session(test_engine) as cleanup:
            ids = select(WalletTopup.id).where(WalletTopup.user_id == user_id)
            cleanup.execute(delete(PaymentEvent).where(PaymentEvent.wallet_topup_id.in_(ids)))
            cleanup.execute(delete(WalletEntry).where(WalletEntry.user_id == user_id))
            cleanup.execute(delete(WalletTopup).where(WalletTopup.user_id == user_id))
            cleanup.execute(delete(User).where(User.id == user_id))
            cleanup.commit()


@pytest.mark.parametrize("scenario", ["identical_retry", "global_limit", "personal_limit", "invoice_race"])
def test_concurrent_promo_limits_and_invoice_freezing(test_engine, provider, notifications, scenario):
    users, rides, promo_id = [], [], uuid4()
    try:
        with Session(test_engine) as setup:
            for _ in range(2):
                user = User(name="Promo concurrency", email=f"{uuid4()}@example.com", role="rider", password_hash="unused")
                setup.add(user)
                setup.flush()
                users.append(user.id)
            rides.append(completed(setup, users[0]).id)
            rides.append(completed(setup, users[0] if scenario == "personal_limit" else users[1]).id)
            code = "RACE"+uuid4().hex[:12].upper()
            now = datetime.now(timezone.utc)
            setup.add(PromoCode(id=promo_id, code=code, percent_off=10, min_fare=Decimal("80"), max_discount=Decimal("50"),
                                max_uses=1 if scenario == "global_limit" else 100, per_user_limit=1,
                                starts_at=now-timedelta(hours=1), expires_at=now+timedelta(hours=1)))
            setup.commit()
        tasks = [(users[0], rides[0]), (users[1] if scenario == "global_limit" else users[0],
                                      rides[1] if scenario in ("global_limit", "personal_limit") else rides[0])]
        barrier = Barrier(2)
        def attempt(index):
            with Session(test_engine) as db:
                db.execute(text("SET LOCAL lock_timeout = '5s'"))
                user = db.get(User, tasks[index][0])
                barrier.wait(timeout=5)
                response = Response(status_code=201)
                try:
                    if scenario == "invoice_race" and index == 1:
                        prepare_payment(tasks[index][1], PaymentInput(), user, db, provider)
                        return 200
                    apply_promo(tasks[index][1], PromoInput(code=code), user, db, response, notifications)
                    return response.status_code
                except HTTPException as error:
                    return error.status_code
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(attempt, range(2)))
        with Session(test_engine) as check:
            used = check.scalars(select(PromoRedemption).where(PromoRedemption.promo_id == promo_id)).all()
            if scenario == "invoice_race":
                assert results[1] == 200 and results[0] in (201, 409)
                payment = check.scalar(select(Payment).where(Payment.ride_id == rides[0]))
                assert payment.amount == (Decimal("93.94") if used else Decimal("104.38"))
                assert provider.intents[payment.stripe_payment_intent_id]["amount"] == int(payment.amount*100)
            else:
                assert sorted(results) == ([200, 201] if scenario == "identical_retry" else [201, 409])
                assert len(used) == 1
    finally:
        with Session(test_engine) as cleanup:
            payment_ids = select(Payment.id).where(Payment.ride_id.in_(rides))
            cleanup.execute(delete(PaymentEvent).where(PaymentEvent.payment_id.in_(payment_ids)))
            cleanup.execute(delete(Payment).where(Payment.ride_id.in_(rides)))
            cleanup.execute(delete(PromoRedemption).where(PromoRedemption.promo_id == promo_id))
            cleanup.execute(delete(PromoCode).where(PromoCode.id == promo_id))
            cleanup.execute(delete(Ride).where(Ride.id.in_(rides)))
            cleanup.execute(delete(User).where(User.id.in_(users)))
            cleanup.commit()
