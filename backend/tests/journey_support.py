"""Owned local services for Day 13 API journeys; all durable data uses _test."""
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
from queue import Queue
import os
import socket
import subprocess
import tempfile
from threading import Thread
import time
from types import SimpleNamespace
from uuid import uuid4

from aiosmtpd.controller import Controller
from celery import Celery
import httpx
from pydantic import SecretStr
import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
import uvicorn
from websockets.sync.client import connect

from app import security
from app.auth import COOKIE_NAME
from app.config import get_settings
from app.database import get_db
from app.events import EventPublisher, get_event_publisher
from app.history import get_receipt_sender
from app.main import app
from app.models import Driver, Payment, PaymentEvent, PromoCode, PromoRedemption, ReceiptEmail, Review, Ride, User, WalletEntry, WalletTopup
from app.payment_gateway import get_payment_gateway
from app.realtime import RealtimeStore, get_realtime_store
from app.ride_schemas import RouteMetrics
from app.routing import get_route_provider
from app.security import RateLimiter
from test_wallet_promos import SIGNING_SECRET, TestProvider

ORIGIN = "http://127.0.0.1:5173"
POINT = {"latitude": 28.614, "longitude": 77.209}
PARAMS = {"origin": "28.6139,77.2090", "dest": "28.6129,77.2295"}
PASSWORD = "day13-fixture-password-only"


class ControlledRoutes:
    calls = 0

    def route(self, pickup, destination):
        self.calls += 1
        return RouteMetrics(distance_meters=3982, duration_secs=396)


@pytest.fixture
def journey_server(test_engine, monkeypatch):
    run = uuid4().hex
    prefix = f"cab_booking:journey:{run}"
    settings = get_settings()
    for key, value in {"cookie_secure": False, "realtime_channel_prefix": prefix,
                       "websocket_session_check_seconds": .1, "websocket_sync_seconds": 1,
                       "stripe_secret_key": SecretStr("sk_test_day13_fixture_only"),
                       "stripe_publishable_key": "pk_test_day13_fixture_only",
                       "stripe_webhook_secret": SecretStr(SIGNING_SECRET), "receipt_email_enabled": False}.items():
        monkeypatch.setattr(settings, key, value)
    limiter = RateLimiter(settings.redis_url.get_secret_value(), prefix + ":limits", "day13-counter-secret")
    publisher = EventPublisher(settings.redis_url.get_secret_value(), prefix)
    assert limiter.client.ping()
    monkeypatch.setattr(security, "get_rate_limiter", lambda: limiter)
    routes, payments = ControlledRoutes(), TestProvider()
    saved_overrides = app.dependency_overrides.copy()
    server = thread = listener = worker = smtp = producer = log = None
    stack = ExitStack()
    campaign_id = uuid4()

    def request_db():
        with Session(test_engine) as db:
            yield db

    app.dependency_overrides.update({get_db: request_db, get_realtime_store: lambda: RealtimeStore(test_engine),
                                    get_event_publisher: lambda: publisher, get_route_provider: lambda: routes,
                                    get_payment_gateway: lambda: payments})
    environment = SimpleNamespace(run=run, engine=test_engine, routes=routes, payments=payments, limiter=limiter,
                                  messages=Queue(), campaign="DAY13" + run[:10].upper(), accounts={})
    try:
        with Session(test_engine) as db:
            now = datetime.now(timezone.utc)
            db.add(PromoCode(id=campaign_id, code=environment.campaign, percent_off=10, min_fare=80, max_discount=50,
                             max_uses=100, per_user_limit=1, starts_at=now-timedelta(hours=1), expires_at=now+timedelta(hours=1)))
            db.commit()
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        environment.base = f"http://127.0.0.1:{port}"
        server = uvicorn.Server(uvicorn.Config(app, log_level="error", proxy_headers=False, ws_max_size=2048))
        thread = Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        deadline = time.monotonic() + 5
        while not server.started and thread.is_alive() and time.monotonic() < deadline: time.sleep(.01)
        assert server.started, "Journey HTTP server did not start."

        def account(label, role="rider"):
            client = stack.enter_context(httpx.Client(base_url=environment.base, headers={"Origin": ORIGIN}, timeout=8))
            result = client.post("/api/auth/register", json={"name": "Journey " + label, "email": f"{label}.{run}@example.com",
                                                           "password": PASSWORD, "role": role})
            assert result.status_code == 201
            environment.accounts[label] = result.json()
            return client

        def websocket(client):
            user = client.get("/api/auth/me").json()
            return stack.enter_context(connect(f"ws://127.0.0.1:{port}/api/ws/{user['role']}/{user['id']}", origin=ORIGIN,
                additional_headers={"Cookie": f"{COOKIE_NAME}={client.cookies.get(COOKIE_NAME)}"}, max_queue=64, open_timeout=3, close_timeout=1))

        def start_mail_worker():
            nonlocal smtp, producer, worker, log
            assert worker is None
            class Catcher:
                async def handle_DATA(self, server, session, envelope):
                    environment.messages.put(envelope.original_content)
                    return "250 Accepted by Day 13 local catcher"
            with socket.socket() as mail_socket:
                mail_socket.bind(("127.0.0.1", 0))
                mail_port = mail_socket.getsockname()[1]
            smtp = Controller(Catcher(), hostname="127.0.0.1", port=mail_port)
            smtp.start()
            monkeypatch.setattr(settings, "receipt_email_enabled", True)
            task_prefix = prefix + ":tasks:"
            producer = Celery("day13", broker=settings.redis_url.get_secret_value())
            producer.conf.update(task_ignore_result=True, broker_transport_options={"global_keyprefix": task_prefix})
            def publish(job): producer.send_task("cab_booking.send_receipt_email", args=[str(job)], queue="receipts", ignore_result=True)
            app.dependency_overrides[get_receipt_sender] = lambda: publish
            env = {**os.environ, "DATABASE_URL": test_engine.url.render_as_string(hide_password=False),
                   "RECEIPT_EMAIL_ENABLED": "true", "SMTP_HOST": "127.0.0.1", "SMTP_PORT": str(mail_port),
                   "SMTP_STARTTLS": "false", "SMTP_USERNAME": "", "SMTP_PASSWORD": "",
                   "CELERY_KEY_PREFIX": task_prefix, "CELERY_BROKER_URL": settings.redis_url.get_secret_value()}
            backend = Path(__file__).resolve().parents[1]
            log = tempfile.TemporaryFile(mode="w+")
            worker = subprocess.Popen([str(backend / ".venv/bin/python"), "-m", "celery", "-A", "app.tasks:celery_app",
                "worker", "--pool=solo", "--concurrency=1", "--loglevel=WARNING", "--without-gossip", "--without-mingle", "--without-heartbeat"],
                cwd=backend, env=env, stdout=log, stderr=subprocess.STDOUT)

        environment.account, environment.websocket, environment.start_mail_worker = account, websocket, start_mail_worker
        yield environment
    finally:
        stack.close()
        if server: server.should_exit = True
        if thread: thread.join(timeout=6)
        if listener: listener.close()
        if worker:
            worker.terminate()
            try: worker.wait(timeout=8)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait(timeout=3)
        if log: log.close()
        if smtp: smtp.stop()
        if producer: producer.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved_overrides)
        keys = list(limiter.client.scan_iter(match=prefix + ":*"))
        if keys: limiter.client.delete(*keys)
        limiter.close()
        publisher.close()
        with Session(test_engine) as db:
            users = select(User.id).where(User.email.like(f"%.{run}@example.com"))
            rides = select(Ride.id).where(Ride.rider_id.in_(users))
            invoices = select(Payment.id).where(Payment.ride_id.in_(rides))
            topups = select(WalletTopup.id).where(WalletTopup.user_id.in_(users))
            db.execute(delete(PaymentEvent).where(PaymentEvent.payment_id.in_(invoices) | PaymentEvent.wallet_topup_id.in_(topups)))
            for model in (ReceiptEmail, Review, PromoRedemption): db.execute(delete(model).where(model.ride_id.in_(rides)))
            db.execute(delete(WalletEntry).where(WalletEntry.user_id.in_(users)))
            db.execute(delete(WalletTopup).where(WalletTopup.user_id.in_(users)))
            db.execute(delete(Payment).where(Payment.ride_id.in_(rides)))
            db.execute(delete(Ride).where(Ride.rider_id.in_(users)))
            db.execute(delete(Driver).where(Driver.user_id.in_(users)))
            db.execute(delete(User).where(User.id.in_(users)))
            db.execute(delete(PromoCode).where(PromoCode.id == campaign_id))
            db.commit()
        assert thread is None or not thread.is_alive(), "Journey server did not stop."
