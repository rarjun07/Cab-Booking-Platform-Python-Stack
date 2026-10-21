"""Bounded API requests and shared, atomic Redis quotas with private keys."""
from functools import lru_cache
import asyncio
import hashlib
import hmac
import math

from anyio import to_thread
from fastapi import HTTPException
from redis import Redis
from redis.backoff import NoBackoff
from redis.exceptions import RedisError
from redis.retry import Retry
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse

from app.config import get_settings

# Check every bucket before incrementing any, then set expiry in the same Redis
# script. Denied traffic cannot renew a window or create non-expiring counters.
QUOTA_SCRIPT = """
local retry = 0
for i, key in ipairs(KEYS) do
  local count = tonumber(redis.call('GET', key) or '0')
  local window = tonumber(ARGV[(i-1)*2+2])
  if count >= tonumber(ARGV[(i-1)*2+1]) then
    local ttl = redis.call('PTTL', key)
    if ttl < 0 then redis.call('PEXPIRE', key, window); ttl = window end
    retry = math.max(retry, math.max(ttl, 1))
  end
end
if retry > 0 then return retry end
for i, key in ipairs(KEYS) do
  local count = redis.call('INCR', key)
  if count == 1 or redis.call('PTTL', key) < 0 then
    redis.call('PEXPIRE', key, tonumber(ARGV[(i-1)*2+2]))
  end
end
return 0
"""


class RateLimiter:
    def __init__(self, redis_url, prefix, secret):
        self.prefix, self.secret = prefix, secret.encode()
        self.client = Redis.from_url(redis_url, protocol=2, socket_timeout=.5, socket_connect_timeout=.5,
                                     retry=Retry(NoBackoff(), 0))

    def key(self, bucket, identity):
        digest = hmac.new(self.secret, f"rate-limit:{bucket}:{identity}".encode(), hashlib.sha256).hexdigest()
        return f"{self.prefix}:{bucket}:{digest}"

    def check(self, policies):
        keys = [self.key(bucket, identity) for bucket, identity, _, _ in policies]
        arguments = [value for _, _, limit, seconds in policies for value in (limit, seconds * 1000)]
        try:
            retry_ms = self.client.eval(QUOTA_SCRIPT, len(keys), *keys, *arguments)
        except RedisError:
            # No process-local fallback that could silently bypass shared quotas.
            raise HTTPException(503, "Request protection is unavailable. Please retry shortly.", headers={"Retry-After": "5"}) from None
        if retry_ms:
            raise HTTPException(429, "Too many requests. Please wait before trying again.",
                                headers={"Retry-After": str(max(1, math.ceil(retry_ms / 1000)))})

    def close(self):
        self.client.close()


@lru_cache
def get_rate_limiter():
    settings = get_settings()
    return RateLimiter(settings.redis_url.get_secret_value(), settings.rate_limit_prefix,
                       settings.jwt_secret.get_secret_value())


def request_policies(path, method, peer):
    policies = [("api", peer, 240, 60)]
    if method not in {"GET", "HEAD", "OPTIONS"}:
        policies.append(("writes", peer, 60, 60))
        if path == "/api/auth/login": policies.append(("login_ip", peer, 10, 60))
        elif path == "/api/auth/register": policies.append(("register", peer, 5, 60))
        elif path.endswith("/payment-intent") or path == "/api/wallet/topups": policies.append(("checkout", peer, 15, 60))
    if path == "/api/rides/estimate" or path.endswith("/route"):
        policies.append(("estimates", peer, 20, 60))
    if path.endswith("/receipt.pdf") or path.endswith("/receipt-email"):
        policies.append(("documents", peer, 20, 60))
    return policies


class RequestGuard:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in {"http", "websocket"} or not scope["path"].startswith("/api/"):
            return await self.app(scope, receive, send)
        path = scope["path"].rstrip("/")
        peer = (scope.get("client") or ("unknown", 0))[0]
        if scope["type"] == "websocket":
            try:
                await to_thread.run_sync(get_rate_limiter().check, [("ws_handshake", peer, 30, 60)])
            except HTTPException as error:
                await send({"type": "websocket.close", "code": 1008 if error.status_code == 429 else 1013})
                return
            return await self.app(scope, receive, send)

        async def protected_send(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                if "no-store" not in {part.strip().lower() for part in headers.get("Cache-Control", "").split(",")}:
                    headers["Cache-Control"] = "no-store"
                headers["X-Content-Type-Options"] = "nosniff"
                headers["Referrer-Policy"] = "no-referrer"
                headers["X-Frame-Options"] = "DENY"
            await send(message)

        if path == "/api/health":
            return await self.app(scope, receive, protected_send)
        webhook = path == "/api/webhooks/stripe"
        headers = Headers(scope=scope)
        maximum = 262144 if webhook else get_settings().max_request_body_bytes
        try:
            if headers.get("content-length") is not None:
                try:
                    length = int(headers["content-length"])
                    if length < 0: raise ValueError
                except ValueError:
                    raise HTTPException(400, "Invalid request length.") from None
                if length > maximum:
                    raise HTTPException(413, "Request body is too large.")
            if not webhook:
                await to_thread.run_sync(get_rate_limiter().check, request_policies(path, scope["method"], peer))
            chunks, size = [], 0
            async with asyncio.timeout(10):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect": return
                    chunk = message.get("body", b"")
                    size += len(chunk)
                    if size > maximum:
                        raise HTTPException(413, "Request body is too large.")
                    chunks.append(chunk)
                    if not message.get("more_body", False): break
            body = b"".join(chunks)
            if body and not webhook:
                media = headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if media != "application/json" and not (media.startswith("application/") and media.endswith("+json")):
                    raise HTTPException(415, "Send the request as application/json.")
        except TimeoutError:
            return await JSONResponse({"detail": "Request body timed out."}, status_code=408)(scope, receive, protected_send)
        except HTTPException as error:
            return await JSONResponse({"detail": error.detail}, status_code=error.status_code, headers=error.headers)(scope, receive, protected_send)

        consumed = False
        async def replay():
            nonlocal consumed
            if not consumed:
                consumed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()
        return await self.app(scope, replay, protected_send)
