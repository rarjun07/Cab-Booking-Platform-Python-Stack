"""Real HTTP/WS/container checks for our LOCAL Compose stack; cleans its own account.

Run with backend/.venv/bin/python scripts/smoke_compose.py [--restart].
No routing, Stripe or external email calls are made. --restart only restarts this
Compose project's services; it never deletes volumes or touches native services.
"""
import argparse
import json
from pathlib import Path
import secrets
import subprocess
import time
from uuid import uuid4

import httpx
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://127.0.0.1:8080"
COMPOSE = ["docker", "compose", "--project-name", "cab-booking-platform", "-f", str(ROOT / "compose.yaml")]


def compose(*args, code=None):
    result = subprocess.run([*COMPOSE, *args], input=code, text=True, cwd=ROOT,
                            capture_output=True, timeout=90)
    if result.returncode:
        # Avoid spilling container environment values/connection errors on failure.
        raise RuntimeError("Compose check failed: " + " ".join(args[:3]))
    return result.stdout


def in_backend(code):
    return compose("exec", "-T", "backend", "python", "-", code=code)


def run(restart=False):
    email = f"compose-smoke-{uuid4().hex}@example.com"
    password = secrets.token_urlsafe(24)
    with httpx.Client(base_url=ORIGIN, headers={"Origin": ORIGIN}, timeout=10, trust_env=False) as client:
        try:
            assert client.get("/").status_code == 200
            health = client.get("/api/health")
            assert health.status_code == 200 and health.json() == {"status": "ok"}
            assert client.get("/api/does-not-exist").status_code == 404
            assert client.get("/api/auth/me").status_code == 401
            assert client.post("/api/auth/logout", headers={"Origin": "https://untrusted.example"}).status_code == 403
            registered = client.post("/api/auth/register", json={
                "name": "Compose smoke account", "email": email, "password": password, "role": "rider"})
            assert registered.status_code == 201, f"Registration status: {registered.status_code}"
            user_id = registered.json()["id"]
            cookie_header = registered.headers["set-cookie"].lower()
            assert "httponly" in cookie_header and "path=/api" in cookie_header and "samesite=lax" in cookie_header
            assert client.get("/api/auth/me").json()["id"] == user_id
            token = client.cookies.get("cab_session")
            with connect(f"ws://127.0.0.1:8080/api/ws/rider/{user_id}", origin=ORIGIN,
                         additional_headers={"Cookie": f"cab_session={token}"},
                         proxy=None, open_timeout=10) as socket:
                assert json.loads(socket.recv(timeout=10)) == {"type": "ready"}
                socket.send(json.dumps({"type": "ping"}))
                assert json.loads(socket.recv(timeout=10)) == {"type": "pong"}
            print("PASS: React, API, origins, PostgreSQL registration/cookie and proxied WebSocket")

            # IP spoofing cannot escape the register quota: nginx overwrites XFF.
            for index in range(4):
                response = client.post("/api/auth/register", json={},
                                       headers={"X-Forwarded-For": f"198.51.100.{index + 1}"})
                assert response.status_code == 422
            limited = client.post("/api/auth/register", json={}, headers={"X-Forwarded-For": "203.0.113.1"})
            assert limited.status_code == 429 and int(limited.headers["Retry-After"]) > 0
            print("PASS: forwarded-header spoofing cannot bypass the Redis registration limit")

            in_backend('''
import os, time
from uuid import uuid4
from sqlalchemy import text
from app.database import get_engine
from app.receipts import render_receipt_pdf
from app.tasks import celery_app, send_receipt_email
assert os.getuid() != 0
with get_engine().connect() as db:
    role = db.execute(text("SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname=current_user")).one()
    assert not any(role)
    assert db.scalar(text("SELECT version_num FROM alembic_version")) == '0009_query_indexes'
    assert db.scalar(text("SELECT ST_Distance(ST_SetSRID(ST_MakePoint(0,0),4326)::geography, ST_SetSRID(ST_MakePoint(0,1),4326)::geography)")) > 100000
pdf = render_receipt_pdf(dict(ride_id=str(uuid4()), rider='Container rider', driver='Container driver',
    requested_at='2026-10-20T00:00:00+00:00', pickup='28.6, 77.2', destination='28.7, 77.3',
    amount='100.00', amount_label='Estimated fare', distance='4 km', duration='10 min',
    payment_status='not_paid', paid_at=None))
assert pdf.startswith(b'%PDF-') and len(pdf) > 1000
def count():
    stats = celery_app.control.inspect(timeout=2).stats() or {}
    return sum(item.get('total', {}).get('cab_booking.send_receipt_email', 0) for item in stats.values())
before = count()
assert celery_app.control.ping(timeout=3)
# A nonexistent job exercises broker delivery without generating or emailing data.
send_receipt_email.delay(str(uuid4()))
for attempt in range(15):
    if count() > before:
        break
    time.sleep(0.5)
else:
    raise AssertionError('Receipt worker did not consume the smoke task')
print('PASS: non-root API, restricted SQL role, migrations, PostGIS, Linux PDF and actual Celery task')
''')
            print("PASS: non-root API, restricted SQL role, migrations, PostGIS, Linux PDF and actual Celery task")

            if restart:
                compose("restart", "database", "redis")
                compose("up", "-d", "--no-deps", "--force-recreate", "backend")
                for attempt in range(50):
                    try:
                        response = client.get("/api/auth/me")
                        if response.status_code == 200 and response.json()["id"] == user_id:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(1)
                else:
                    raise AssertionError("Account/session did not recover after restart")
                print("PASS: account/session survive DB/Redis restart and API recreation behind nginx")

            assert client.post("/api/auth/logout").status_code == 204
            assert client.get("/api/auth/me", headers={"Cookie": f"cab_session={token}"}).status_code == 401
            assert client.post("/api/auth/login", json={"email": email, "password": password}).status_code == 200
            assert client.post("/api/auth/logout").status_code == 204
            print("PASS: login, logout and revoked cookie replay")
        finally:
            in_backend(f'''
from sqlalchemy import delete, select
from app.database import get_engine
from app.models import User
with get_engine().begin() as db:
    db.execute(delete(User).where(User.email == {email!r}))
    assert db.scalar(select(User.id).where(User.email == {email!r})) is None
print('Smoke account and cascading sessions removed')
''')
            print("CLEANUP: removed only this run's generated smoke account and sessions")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restart", action="store_true")
    run(parser.parse_args().restart)
