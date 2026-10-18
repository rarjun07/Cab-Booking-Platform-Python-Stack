from datetime import datetime, timedelta, timezone
from decimal import Decimal
import io
import smtplib
from uuid import UUID, uuid4

from geoalchemy2 import WKTElement
from pydantic import ValidationError
from pypdf import PdfReader
import pytest
from sqlalchemy import func, select

from app.auth import password_hasher
from app.config import Settings, get_settings
from app.history import get_receipt_sender
from app.main import app
from app.models import Driver, Payment, ReceiptEmail, Ride, User
from app.receipts import no_external_resources
from app.tasks import deliver_receipt


@pytest.fixture
def past_trips(client, db, account, monkeypatch):
    monkeypatch.setattr(get_settings(), "receipt_email_enabled", False)
    registered = client.post("/api/auth/register", json=account)
    assert registered.status_code == 201
    rider_id = UUID(registered.json()["id"])
    driver = User(name="Receipt Driver", email="receipt-driver@example.com", role="driver",
                  password_hash=password_hasher.hash(account["password"]))
    other = User(name="Private", email="private-history@example.com", role="rider", password_hash="unused")
    db.add_all([driver, other])
    db.flush()
    db.add(Driver(user_id=driver.id, vehicle_info={}))
    db.flush()
    rides = []
    now = datetime.now(timezone.utc)
    for index, status in enumerate(["completed", "completed", "cancelled", "requested"]):
        ride = Ride(id=UUID(int=index + 1), rider_id=rider_id, driver_id=driver.id if status != "requested" else None,
                    pickup_point=WKTElement("POINT(77.209 28.6139)", srid=4326),
                    drop_point=WKTElement("POINT(77.2295 28.6129)", srid=4326), fare_estimate=Decimal("104.38"),
                    distance_meters=3982, duration_secs=396, status=status, created_at=now)
        db.add(ride)
        rides.append(ride)
    foreign = Ride(rider_id=other.id, status="completed", fare_estimate=Decimal("99.00"),
                   pickup_point=WKTElement("POINT(77.209 28.6139)", srid=4326),
                   drop_point=WKTElement("POINT(77.2295 28.6129)", srid=4326))
    db.add(foreign)
    db.flush()
    return rides, rider_id, driver, foreign


@pytest.fixture
def sender(past_trips, monkeypatch):
    monkeypatch.setattr(get_settings(), "receipt_email_enabled", True)
    calls = []
    app.dependency_overrides[get_receipt_sender] = lambda: calls.append
    yield calls
    app.dependency_overrides.pop(get_receipt_sender, None)


def test_history_has_stable_pagination_and_only_owned_terminal_rides(client, past_trips):
    rides, _, _, foreign = past_trips
    seen = []
    cursor = None
    for _ in range(3):
        response = client.get("/api/rides/history", params={"limit": 1, **({"cursor": cursor} if cursor else {})})
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        page = response.json()
        seen.extend(item["id"] for item in page["items"])
        cursor = page["next_cursor"]
    assert seen == [str(rides[i].id) for i in (2, 1, 0)] and cursor is None
    assert client.get("/api/rides/history", params={"cursor": str(foreign.id)}).status_code == 422
    assert client.get("/api/rides/history", params={"cursor": str(rides[3].id)}).status_code == 422
    for limit in (0, 51):
        assert client.get("/api/rides/history", params={"limit": limit}).status_code == 422
    page = client.get("/api/rides/history").json()
    assert [item["receipt_available"] for item in page["items"]] == [False, True, True]
    assert all(item["payment_status"] is None for item in page["items"])


def test_assigned_driver_has_history_and_pdf_but_not_other_trips(client, past_trips, account):
    rides, _, driver, foreign = past_trips
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"email": driver.email, "password": account["password"]}).status_code == 200
    assert {r["id"] for r in client.get("/api/rides/history").json()["items"]} == {str(r.id) for r in rides[:3]}
    assert client.get(f"/api/rides/{rides[0].id}/receipt.pdf").status_code == 200
    assert client.get(f"/api/rides/{foreign.id}/receipt.pdf").status_code == 404


def test_pdf_is_readable_and_does_not_claim_unpaid_trip_was_paid(client, past_trips, db):
    rides, rider_id, _, _ = past_trips
    db.get(User, rider_id).name = '<img src="file:///private/example"> & Rider'
    db.flush()
    result = client.get(f"/api/rides/{rides[0].id}/receipt.pdf")
    assert result.status_code == 200 and result.content.startswith(b"%PDF-")
    assert result.headers["content-type"] == "application/pdf"
    assert result.headers["cache-control"] == "private, no-store"
    assert result.headers["x-content-type-options"] == "nosniff"
    assert f'ride-{rides[0].id}.pdf' in result.headers["content-disposition"]
    reader = PdfReader(io.BytesIO(result.content))
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    for value in ("Trip statement", "104.38", "not proof of payment", str(rides[0].id), "Estimated fare"):
        assert value in text
    assert "<img" in text and "& Rider" in text
    assert "password" not in text and "private-history@example.com" not in text
    with pytest.raises(ValueError):
        no_external_resources("file:///private/example")


def test_paid_pdf_and_history_use_recorded_invoice_not_estimate(client, past_trips, db):
    ride = past_trips[0][0]
    db.add(Payment(ride_id=ride.id, amount=Decimal("120.25"), status="succeeded", paid_at=datetime.now(timezone.utc)))
    db.flush()
    result = client.get(f"/api/rides/{ride.id}/receipt.pdf")
    text = PdfReader(io.BytesIO(result.content)).pages[0].extract_text()
    assert "Test payment receipt" in text and "120.25" in text
    assert "104.38" not in text and "test-payment ledger" in text
    item = next(i for i in client.get("/api/rides/history").json()["items"] if i["id"] == str(ride.id))
    assert item["payment_amount"] == "120.25" and item["payment_status"] == "succeeded"


def test_receipts_require_completed_owned_ride_and_auth(client, past_trips):
    rides, _, _, foreign = past_trips
    for suffix in ("receipt.pdf", "receipt-email"):
        assert client.get(f"/api/rides/{foreign.id}/{suffix}").status_code == 404
        assert client.get(f"/api/rides/{uuid4()}/{suffix}").status_code == 404
        assert client.get(f"/api/rides/{rides[2].id}/{suffix}").status_code == 409
        assert client.get(f"/api/rides/{rides[3].id}/{suffix}").status_code == 409
    client.post("/api/auth/logout")
    for path in ("/api/rides/history", "/api/receipts/config", f"/api/rides/{rides[0].id}/receipt.pdf"):
        assert client.get(path).status_code == 401


def test_email_disabled_creates_nothing_and_origin_and_recipient_are_guarded(client, past_trips, db):
    path = f"/api/rides/{past_trips[0][0].id}/receipt-email"
    assert client.get("/api/receipts/config").json() == {"email_enabled": False}
    assert client.post(path, json={}).status_code == 503
    assert client.post(path, json={}, headers={"Origin": "https://untrusted.example"}).status_code == 403
    assert client.post(path, json={"recipient": "someone-else@example.com"}).status_code == 422
    assert db.scalar(select(func.count()).select_from(ReceiptEmail)) == 0


def test_email_retries_reuse_job_and_new_payment_state_gets_new_snapshot(client, past_trips, sender, db, account):
    ride = past_trips[0][0]
    path = f"/api/rides/{ride.id}/receipt-email"
    assert client.get(path).json() is None
    first = client.post(path, json={})
    second = client.post(path, json={})
    assert first.status_code == second.status_code == 202
    assert first.json()["id"] == second.json()["id"] and len(sender) == 2
    job = db.get(ReceiptEmail, UUID(first.json()["id"]))
    assert job.recipient == account["email"] and job.status == "queued"
    job.status, job.sent_at = "sent", datetime.now(timezone.utc)
    db.flush()
    assert client.post(path, json={}).status_code == 200 and len(sender) == 2
    db.add(Payment(ride_id=ride.id, amount=Decimal("104.38"), status="succeeded"))
    db.flush()
    updated = client.post(path, json={})
    assert updated.status_code == 202 and updated.json()["id"] != first.json()["id"]
    assert job.snapshot["payment_status"] == "not_paid"
    assert db.scalar(select(func.count()).select_from(ReceiptEmail)) == 2


def test_broker_failure_preserves_job_for_retry(client, past_trips, sender, db):
    def unavailable(job_id):
        raise OSError("private provider diagnostic")
    app.dependency_overrides[get_receipt_sender] = lambda: unavailable
    path = f"/api/rides/{past_trips[0][0].id}/receipt-email"
    result = client.post(path, json={})
    assert result.status_code == 503 and "private provider" not in result.text
    saved_id = client.get(path).json()["id"]
    app.dependency_overrides[get_receipt_sender] = lambda: sender.append
    retry = client.post(path, json={})
    assert retry.status_code == 202 and retry.json()["id"] == saved_id
    assert db.scalar(select(func.count()).select_from(ReceiptEmail)) == 1


def test_worker_generates_pdf_once_and_duplicate_delivery_is_skipped(client, past_trips, sender, db):
    result = client.post(f"/api/rides/{past_trips[0][0].id}/receipt-email", json={})
    job_id = result.json()["id"]
    captured = []
    def send(job, pdf):
        captured.append((job.recipient, pdf))
    assert deliver_receipt(job_id, db.connection(), send) is False
    assert deliver_receipt(job_id, db.connection(), send) is False
    db.expire_all()
    assert len(captured) == 1 and captured[0][1].startswith(b"%PDF-")
    job = db.get(ReceiptEmail, UUID(job_id))
    assert job.status == "sent" and job.attempts == 1 and job.sent_at


def test_failed_worker_has_bounded_retries_and_safe_manual_retry(client, past_trips, sender, db):
    path = f"/api/rides/{past_trips[0][0].id}/receipt-email"
    job_id = client.post(path, json={}).json()["id"]
    def fail(job, pdf):
        raise smtplib.SMTPException("private diagnostic")
    assert deliver_receipt(job_id, db.connection(), fail) is True
    assert deliver_receipt(job_id, db.connection(), fail) is True
    assert deliver_receipt(job_id, db.connection(), fail) is False
    db.expire_all()
    job = db.get(ReceiptEmail, UUID(job_id))
    assert job.status == "failed" and job.attempts == 3
    assert client.post(path, json={}).status_code == 429
    job.last_attempt_at -= timedelta(minutes=2)
    db.flush()
    retry = client.post(path, json={})
    assert retry.status_code == 202 and retry.json()["id"] == job_id and retry.json()["attempts"] == 0


def test_remote_plaintext_smtp_and_partial_credentials_are_rejected():
    with pytest.raises(ValidationError):
        Settings(smtp_host="mail.example.com", smtp_starttls=False)
    with pytest.raises(ValidationError):
        Settings(smtp_username="only-one-setting", smtp_password=None)
