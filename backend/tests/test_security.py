import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import time
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from app import security
from app.config import Settings, get_settings
from app.security import RateLimiter, RequestGuard, request_policies
from app.driver_schemas import VehicleInfo
from app.ride_schemas import Coordinate


@pytest.fixture
def limiter(monkeypatch):
    value = RateLimiter(get_settings().redis_url.get_secret_value(), f"cab_booking:test:limits:{uuid4().hex}", "local-test-counter-secret")
    assert value.client.ping()
    monkeypatch.setattr(security, "get_rate_limiter", lambda: value)
    yield value
    keys = list(value.client.scan_iter(match=f"{value.prefix}:*"))
    if keys: value.client.delete(*keys)
    value.close()


def test_shared_redis_quota_is_atomic_across_clients_and_does_not_extend_on_denial(limiter):
    other = RateLimiter(get_settings().redis_url.get_secret_value(), limiter.prefix, "local-test-counter-secret")
    policy = [("concurrent", "peer@example.com", 5, 60)]
    try:
        def attempt(index):
            try:
                (limiter if index % 2 else other).check(policy)
                return 200
            except HTTPException as error: return error.status_code
        with ThreadPoolExecutor(max_workers=8) as workers:
            results = list(workers.map(attempt, range(20)))
        assert results.count(200) == 5 and results.count(429) == 15
        key = limiter.key("concurrent", "peer@example.com")
        assert int(limiter.client.get(key)) == 5
        assert "peer@example.com" not in key
        ttl = limiter.client.pttl(key)
        assert 0 < ttl <= 60000
        with pytest.raises(HTTPException) as caught: other.check(policy)
        assert 1 <= int(caught.value.headers["Retry-After"]) <= 60
        assert limiter.client.pttl(key) <= ttl
        limiter.client.pexpire(key, 1)
        time.sleep(.02)
        other.check(policy)
        assert int(limiter.client.get(key)) == 1
    finally:
        other.close()


def test_denied_bucket_does_not_consume_other_quota_and_legacy_no_ttl_is_repaired(limiter):
    limiter.check([("small", "peer", 1, 60)])
    with pytest.raises(HTTPException):
        limiter.check([("large", "peer", 10, 60), ("small", "peer", 1, 60)])
    assert limiter.client.get(limiter.key("large", "peer")) is None
    key = limiter.key("stale", "peer")
    limiter.client.set(key, 1)
    with pytest.raises(HTTPException): limiter.check([("stale", "peer", 1, 60)])
    assert 0 < limiter.client.pttl(key) <= 60000


def test_login_ip_limit_runs_before_password_check_and_ignores_spoofed_forwarding_headers(client, limiter):
    for index in range(10):
        response = client.post("/api/auth/login", json={"email": "absent@example.com", "password": "incorrect"},
                               headers={"X-Forwarded-For": f"192.0.2.{index}"})
        assert response.status_code == 401
    response = client.post("/api/auth/login", json={"email": "other@example.com", "password": "private-invalid-password"})
    assert response.status_code == 429 and int(response.headers["Retry-After"]) > 0
    assert response.headers["cache-control"] == "no-store"
    assert "private-invalid-password" not in response.text


def test_account_limit_uses_normalized_email_independently_of_peer_quota(client, limiter):
    for _ in range(10): limiter.check([("login_account", "rider@example.com", 10, 60)])
    response = client.post("/api/auth/login", json={"email": "RIDER@EXAMPLE.COM", "password": "unused"})
    assert response.status_code == 429


def test_register_limit_counts_invalid_payloads_before_hashing(client, limiter):
    for _ in range(5): assert client.post("/api/auth/register", json={}).status_code == 422
    assert client.post("/api/auth/register", json={}).status_code == 429


def test_actual_get_estimates_are_limited_before_route_parsing(client, limiter, account):
    assert client.post("/api/auth/register", json=account).status_code == 201
    for _ in range(20):
        assert client.get("/api/rides/estimate", params={"origin": "invalid", "dest": "invalid"}).status_code == 422
    response = client.get("/api/rides/estimate", params={"origin": "invalid", "dest": "invalid"})
    assert response.status_code == 429 and int(response.headers["Retry-After"]) > 0


def test_redis_failure_closes_protected_http_but_health_and_stripe_verification_remain_available(client, limiter, monkeypatch):
    def broken(*args): raise RedisConnectionError("private-redis-details")
    monkeypatch.setattr(limiter.client, "eval", broken)
    response = client.get("/api/auth/me")
    assert response.status_code == 503 and response.headers["Retry-After"] == "5"
    assert "private-redis-details" not in response.text
    assert client.get("/api/health").status_code == 200
    assert client.post("/api/webhooks/stripe", content=b"{}").status_code == 400


@pytest.mark.parametrize("method", ["POST", "PUT"])
def test_cors_allows_only_configured_origins_and_implemented_methods(client, method):
    headers = {"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": method,
               "Access-Control-Request-Headers": "content-type"}
    good = client.options("/api/drivers/me", headers=headers)
    assert good.status_code == 200
    assert good.headers["access-control-allow-origin"] == headers["Origin"]
    assert good.headers["access-control-allow-credentials"] == "true"
    bad = client.options("/api/drivers/me", headers={**headers, "Origin": "https://untrusted.example"})
    assert bad.status_code == 400 and "access-control-allow-origin" not in bad.headers
    assert client.options("/api/drivers/me", headers={**headers, "Access-Control-Request-Method": "DELETE"}).status_code == 400
    write = client.post("/api/auth/login", json={}, headers={"Origin": "https://untrusted.example"})
    assert write.status_code == 403 and "access-control-allow-origin" not in write.headers


@pytest.mark.parametrize("case", ["declared", "understated", "chunked"])
def test_request_limit_checks_declared_and_actual_bytes_without_echoing_body(client, case):
    body = b"private-body-" * 6000
    headers = {"Content-Type": "application/json"}
    if case == "understated": headers["Content-Length"] = "1"
    response = client.post("/api/auth/login", content=iter([body[:20000], body[20000:]]) if case == "chunked" else body, headers=headers)
    assert response.status_code == 413 and "private-body-" not in response.text
    assert response.headers["x-content-type-options"] == "nosniff"


def test_invalid_json_media_and_validation_errors_are_safe(client, account):
    assert client.post("/api/auth/login", content=b"{}", headers={"Content-Type": "text/plain"}).status_code == 415
    for name in ("Rider\x00name", "Rider\ud800"):
        payload = {**account, "name": name}
        result = client.post("/api/auth/register", content=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        assert result.status_code == 422 and account["password"] not in result.text
    result = client.post("/api/auth/register", json={**account, "wallet_balance": "1000"})
    assert result.status_code == 422 and account["password"] not in result.text
    assert client.post("/api/auth/login", json={"email": account["email"], "password": "password", "role": "admin"}).status_code == 422


@pytest.mark.parametrize("origins", [[], ["*"], ["null"], ["https://*.example.com"], ["https://user:password@example.com"],
                                   ["https://example.com/"], ["https://example.com?query=1"], ["file://example.com"], ["https://example.com/#fragment"]])
def test_configuration_rejects_unsafe_origin_lists(origins):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="postgresql://unused/unused", jwt_secret="test-only-" * 8, allowed_origins=origins)


def test_config_normalizes_valid_origins_and_response_errors_are_private(client):
    settings = Settings(_env_file=None, database_url="postgresql://unused/unused", jwt_secret="test-only-" * 8,
                        allowed_origins=["https://EXAMPLE.COM:443", "https://example.com", "http://[::1]:5173"])
    assert settings.allowed_origins == ["https://example.com", "http://[::1]:5173"]
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    for key, value in {"cache-control": "no-store", "x-content-type-options": "nosniff", "referrer-policy": "no-referrer", "x-frame-options": "DENY"}.items():
        assert response.headers[key] == value


def test_raw_websocket_handshake_is_rate_limited_before_downstream(limiter):
    messages, calls = [], []
    async def downstream(*args): calls.append(True)
    async def send(message): messages.append(message)
    async def receive(): return {"type": "websocket.connect"}
    async def exercise():
        guard = RequestGuard(downstream)
        scope = {"type": "websocket", "path": "/api/ws/rider/fixture", "client": ("192.0.2.1", 1234)}
        for _ in range(31): await guard(scope, receive, send)
    asyncio.run(exercise())
    assert len(calls) == 30 and messages == [{"type": "websocket.close", "code": 1008}]


def test_sensitive_paths_have_separate_quota_buckets():
    expected = {"/api/auth/login": "login_ip", "/api/auth/register": "register", "/api/rides/estimate": "estimates",
                "/api/rides/id/payment-intent": "checkout", "/api/wallet/topups": "checkout", "/api/rides/id/receipt-email": "documents"}
    for path, bucket in expected.items():
        assert bucket in [policy[0] for policy in request_policies(path, "POST", "peer")]


@pytest.mark.parametrize("value", [True, "28.6", float("nan"), float("inf")])
def test_coordinates_require_finite_json_numbers(value):
    with pytest.raises(ValidationError): Coordinate(latitude=value, longitude=77.2)


@pytest.mark.parametrize("value", ["Vehicle\x00name", "Vehicle\ud800"])
def test_vehicle_details_reject_text_postgresql_cannot_store(value):
    with pytest.raises(ValidationError): VehicleInfo(make=value, model="Test", plate="TEST123")
