"""Real Celery subprocess + Redis + loopback SMTP, with committed test fixtures."""
from decimal import Decimal
from email import policy
from email.parser import BytesParser
import io
import os
from pathlib import Path
from queue import Queue
import socket
import subprocess
import tempfile
import time
from uuid import UUID, uuid4

from aiosmtpd.controller import Controller
from celery import Celery
from fastapi.testclient import TestClient
from geoalchemy2 import WKTElement
from pypdf import PdfReader
from redis import Redis
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.history import get_receipt_sender
from app.main import app
from app.models import ReceiptEmail, Ride, User


def test_receipt_crosses_real_redis_worker_and_local_smtp_once(test_engine, monkeypatch):
    settings = get_settings()
    prefix = f"cab_booking:receipt-test:{uuid4()}:"
    messages = Queue()
    class Capture:
        async def handle_DATA(self, server, session, envelope):
            messages.put(envelope.original_content)
            return "250 Accepted by the local test catcher"

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    smtp = Controller(Capture(), hostname="127.0.0.1", port=port)
    producer = Celery("receipt_test", broker=settings.redis_url.get_secret_value())
    producer.conf.update(task_ignore_result=True, broker_transport_options={"global_keyprefix": prefix})
    redis = Redis.from_url(settings.redis_url.get_secret_value())
    worker = None
    rider_id = None
    backend = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(settings, "receipt_email_enabled", True)

    def request_db():
        with Session(test_engine) as db:
            yield db

    def publish(job_id):
        producer.send_task("cab_booking.send_receipt_email", args=[str(job_id)], queue="receipts", ignore_result=True)

    app.dependency_overrides[get_db] = request_db
    app.dependency_overrides[get_receipt_sender] = lambda: publish
    try:
        assert redis.ping(), "The receipt worker integration test requires local Redis."
        smtp.start()
        env = {**os.environ, "DATABASE_URL": test_engine.url.render_as_string(hide_password=False),
               "RECEIPT_EMAIL_ENABLED": "true", "SMTP_HOST": "127.0.0.1", "SMTP_PORT": str(port),
               "SMTP_STARTTLS": "false", "CELERY_KEY_PREFIX": prefix,
               "CELERY_BROKER_URL": settings.redis_url.get_secret_value(),
               "SMTP_USERNAME": "", "SMTP_PASSWORD": ""}
        # Explicit empty overrides clear any real SMTP credentials from local dotenv.
        with tempfile.TemporaryFile(mode="w+") as log:
            worker = subprocess.Popen([str(backend / ".venv/bin/python"), "-m", "celery", "-A", "app.tasks:celery_app",
                                       "worker", "--pool=solo", "--concurrency=1", "--loglevel=WARNING",
                                       "--without-gossip", "--without-mingle", "--without-heartbeat"],
                                      cwd=backend, env=env, stdout=log, stderr=subprocess.STDOUT)
            with TestClient(app, headers={"Origin": "http://127.0.0.1:5173"}) as client:
                registered = client.post("/api/auth/register", json={"name": "Receipt Worker Demo", "role": "rider",
                                         "email": f"{uuid4()}@example.com", "password": "worker-test-password-long"})
                assert registered.status_code == 201
                rider_id = UUID(registered.json()["id"])
                with Session(test_engine) as db:
                    ride = Ride(rider_id=rider_id, status="completed", fare_estimate=Decimal("104.38"),
                                pickup_point=WKTElement("POINT(77.209 28.6139)", srid=4326),
                                drop_point=WKTElement("POINT(77.2295 28.6129)", srid=4326))
                    db.add(ride)
                    db.commit()
                    ride_id = ride.id
                path = f"/api/rides/{ride_id}/receipt-email"
                requested = client.post(path, json={})
                assert requested.status_code == 202
                job_id = requested.json()["id"]
                # Two published copies must still produce one accepted email.
                duplicate = client.post(path, json={})
                assert duplicate.status_code in (200, 202) and duplicate.json()["id"] == job_id
                deadline = time.monotonic() + 25
                state = None
                while time.monotonic() < deadline and worker.poll() is None:
                    state = client.get(path).json()
                    if state["status"] == "sent":
                        break
                    time.sleep(0.1)
                assert state and state["status"] == "sent", "Local receipt worker did not complete delivery."
                assert state["attempts"] == 1 and state["sent_at"]
                raw = messages.get(timeout=2)
                message = BytesParser(policy=policy.default).parsebytes(raw)
                assert message["To"] == registered.json()["email"]
                attachment, = list(message.iter_attachments())
                assert attachment.get_content_type() == "application/pdf"
                assert attachment.get_filename() == f"ride-{ride_id}.pdf"
                text = PdfReader(io.BytesIO(attachment.get_payload(decode=True))).pages[0].extract_text()
                assert str(ride_id) in text and "not proof of payment" in text
                assert client.post(path, json={}).status_code == 200
                # A graceful shutdown drains any already-received duplicate task.
            worker.terminate()
            worker.wait(timeout=8)
            worker = None
            assert messages.empty()
    finally:
        if worker:
            worker.terminate()
            try:
                worker.wait(timeout=8)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait(timeout=3)
        smtp.stop()
        producer.close()
        keys = list(redis.scan_iter(match=prefix + "*"))
        if keys:
            redis.delete(*keys)  # Only this unique test prefix; never flush Redis.
        redis.close()
        app.dependency_overrides.pop(get_receipt_sender, None)
        app.dependency_overrides.pop(get_db, None)
        if rider_id:
            with Session(test_engine) as db:
                db.execute(delete(ReceiptEmail).where(ReceiptEmail.user_id == rider_id))
                db.execute(delete(Ride).where(Ride.rider_id == rider_id))
                db.execute(delete(User).where(User.id == rider_id))
                db.commit()
