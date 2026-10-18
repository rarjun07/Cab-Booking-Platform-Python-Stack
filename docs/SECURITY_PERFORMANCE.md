# Day 12: request protection and database queries

Day 12 adds shared Redis quotas, bounded request bodies, explicit browser origins, stricter inputs and indexes for the queries used by history, wallet and promos. It also removes a repeated coordinate query from driver offers. FastAPI still owns authentication/authorization and PostgreSQL still owns durable records. No paid service or new dependency is required.

The user requested continuation after the Day 11 manual-review reminder. Those browser/mobile/zoom/screen-reader checks remain pending. The earlier actual Stripe setup/transaction/webhook/rendered-checkout checks also remain pending; this milestone does not verify them.

## Step 1: update and restart locally

Keep the existing PostgreSQL/PostGIS and Redis services running. From the backend terminal:

```bash
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/backend"
source .venv/bin/activate
export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"
python -m alembic upgrade head
python -m alembic current
python -m uvicorn app.main:app --reload --no-proxy-headers --ws-max-size 2048
```

The migration is already applied on this machine; `0009_query_indexes` is the head. If your backend is running, stop that server with Ctrl+C and restart it using the updated command. Reloading Python files does not change Uvicorn's startup flags. Reuse your existing frontend server or run `npm run dev` from `frontend/`.

`--no-proxy-headers` makes local Uvicorn retain the socket peer instead of accepting forwarded client-IP claims. The application itself ignores `X-Forwarded-For`. Through Vite, local requests share the proxy's peer address, so tabs/accounts can share an IP quota. Production deployment must deliberately configure a trusted edge/proxy, strip untrusted forwarded headers and restrict direct backend access; do not enable blanket forwarded-header trust. Deployment is still scheduled for Day 14.

## Step 2: understand the Redis limits

Each Lua script call checks its buckets and increments them atomically. The middleware checks peer buckets together; login checks its normalized-email bucket separately after input validation, so an account-level denial can already have consumed a peer allowance. Within a script call, denial consumes none of its buckets. Multiple backend workers using the same Redis database, prefix and signing secret share their counters. Each bucket expires 60 seconds after its first accepted request; denied checks do not prolong it. This is a fixed window, so a new window permits a new burst.

| Bucket | Default allowance | Identity |
| --- | --- | --- |
| API requests | 240 per 60 seconds | Socket peer IP. |
| API writes | 60 per 60 seconds | Socket peer IP. |
| Login | 10 per 60 seconds | Peer IP, plus a separate normalized email bucket. |
| Registration | 5 per 60 seconds | Peer IP, including invalid requests. |
| Fare estimates | 20 per 60 seconds | Peer IP; existing OSRM cache/throttle also remains. |
| Ride checkout and wallet top-up preparation | 15 per 60 seconds | Peer IP, shared between these actions. |
| PDF/receipt-email endpoints | 20 per 60 seconds | Peer IP, shared between reads/writes. |
| WebSocket connection attempts | 30 per 60 seconds | Peer IP, before authentication/subscription. |

An accepted WebSocket separately allows up to 30 incoming messages in a rolling ten-second window. Crossing that bound closes it with policy code 1008. Existing 2,048-byte message bounds, session rechecks and location-update spacing remain. This is not a total simultaneous-connection cap.

When a quota is reached, HTTP returns `429` with `Retry-After` in seconds. The current React error handlers display the safe backend message; there is no countdown UI. Redis failure returns `503` and `Retry-After: 5` for protected HTTP requests and closes new WebSockets with 1013. There is no local-memory bypass. Existing live subscriptions follow their existing failure/reconnect behavior.

`/api/health` stays available without Redis. Stripe's signed webhook bypasses the IP quotas so a shared provider address or exhausted browser quota cannot prevent payment delivery. Its raw signature verification, canonical test-intent checks, idempotent audit/credits and 256 KiB body bound remain enforced. CORS preflight is handled before the request guard. Infrastructure-wide connection/flood protection is outside these application quotas.

Redis key identities use HMAC-SHA256 with a purpose prefix and the existing secret; raw emails and IP addresses are not stored in key names. Rotating the secret or prefix creates fresh quota identities. Counter keys contain no passwords or request payloads. Tests use a unique test prefix and delete only that prefix's keys; they never flush shared Redis. The implementation targets the existing single Redis server, not a Redis Cluster multi-key script configuration.

The policy values live in `app/security.py`. Existing safe defaults also work without editing `.env`. Optional configuration is documented in `backend/.env.example`:

```dotenv
RATE_LIMIT_PREFIX=cab_booking:limits:v1
MAX_REQUEST_BODY_BYTES=65536
ALLOWED_ORIGINS=["http://127.0.0.1:5173","http://localhost:5173","http://127.0.0.1:8000","http://localhost:8000"]
```

Keep the existing private `REDIS_URL` and `JWT_SECRET` in ignored local configuration. Do not paste credentials into documentation or Git.

## Step 3: understand origins, bodies and validation

CORS allows credentials only for the explicit configured origins and implemented browser methods GET, POST and PUT. Allowed origins are HTTP(S) scheme/host/port values without wildcards, user credentials, paths, queries or fragments. Configuration normalizes host casing/default ports and rejects empty or unsafe lists. The allowed browser request header is Content-Type; Retry-After is exposed to the browser. The Vite same-origin proxy remains the normal local frontend arrangement.

CORS governs browser access to responses. It does not authenticate a caller. The existing allowed-Origin checks still protect state-changing cookie requests; existing session, role and ownership checks still protect data. WebSockets retain their separate Origin/account checks.

For guarded API requests, the default body limit is 64 KiB. The guard checks both declared Content-Length and actual received bytes, including chunked or understated bodies, before downstream parsing. A body taking over ten seconds to finish returns 408. Nonempty ordinary API bodies must use JSON or an application `+json` media type; otherwise the response is 415. Oversized bodies return 413. Stripe payload bytes are replayed unchanged for signature verification.

Handled guarded API responses, including error responses, get `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` and `X-Frame-Options: DENY`. Existing stricter private/no-store receipt headers are retained. This does not claim to configure headers for Vite-served HTML, CORS preflight, or an outer server's unhandled-error response.

Login/registration reject unknown fields. Coordinates require finite JSON numbers, reject booleans/numeric strings and reject extra coordinate fields. Names and vehicle text reject null characters and invalid Unicode before reaching PostgreSQL/JSONB; existing review text protections remain. Validation errors continue to omit submitted input values. Existing quote, payment, promo and wallet owner/pricing checks remain in force.

## Step 4: understand the query changes

An index helps PostgreSQL find matching rows in the requested order. History needs owner plus descending creation time and UUID; a single owner index cannot fully supply that ordering. Migration `0009_query_indexes` adds:

| Index | Query supported |
| --- | --- |
| `ix_rides_rider_history` | Rider's completed/cancelled history, ordered by time and UUID. |
| `ix_rides_driver_history` | Assigned driver's completed/cancelled history in the same order. |
| `ix_wallet_topups_owner_created` | Rider's latest five top-ups. |
| `ix_wallet_entries_owner_created` | Rider's latest ten credits. |
| `ix_promo_redemptions_code_user` | Total/personal usage for a promo. |

The history indexes are partial: only completed/cancelled trips are indexed. The wallet/promo composites replace three redundant single-column indexes while retaining leftmost-key lookup support. Existing uniqueness, auth lookup, active-driver and spatial indexes remain. The migration changes indexes only; upgrading/downgrading does not delete application rows. Ordinary index creation can block writes while building, so a large deployed database needs its own rollout plan.

Driver offers now select their four coordinate values in the nearby-offer query and pass them to `ride_response`. Returning 20 offers makes one coordinate-bearing query, rather than that query plus 20 individual coordinate reads. Authorization/profile/matching checks still perform their own reads; this is not a claim that the entire endpoint executes only one query.

## Step 5: verification and its limits

From `backend/`, with the existing PDF library path and local PostgreSQL/Redis available:

```bash
python -m pytest -q
python -m pip check
python -m alembic check
```

Observed final results: **263 backend tests passed** in 32.79 seconds, with the existing TestClient/HTTPX deprecation warning; dependency consistency and no-schema-drift checks passed. Development migration fingerprints confirmed every existing row across 13 application tables was preserved. No development downgrade or synthetic development wallet credit was performed.

Thirty new security cases exercise real Redis concurrency across two clients, TTL/reset/no-extension behavior, atomic multi-bucket denial, login IP/account and registration limits, Redis failure, forwarded-header claims at the app boundary, CORS success/rejection, declared/actual/chunked body limits, safe validation/configuration, and WebSocket handshake quotas. Existing business-flow tests isolate quotas with a controlled guard to avoid sharing request counters. The dedicated quota tests use real Redis. Additional regressions cover a real TCP WebSocket flood close, nearby-offer coordinate query count, and index migration/data preservation/query plans.

The synthetic query-plan test uses a rolled-back dedicated `_test` transaction with 4,000 rides, 2,000 top-ups and 2,000 credit entries. `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` uses the real planner without disabling sequential scans. Observed warm-cache plans:

| Query | Before | After | Shared hit blocks before → after |
| --- | --- | --- | --- |
| Rider history, six rows | Incremental Sort + Index Scan | History index, no sort | 3 → 3 |
| Driver history, six rows | Sort + Seq Scan | History index, no sort | 86 → 3 |
| Ten wallet entries | Sort + Seq Scan | Owner/time/UUID index, no sort | 24 → 3 |
| Five top-ups | Sort + Seq Scan | Owner/time/UUID index, no sort | 31 → 3 |

Rows/balances were compared across the index upgrade; the downgrade also retained the synthetic rows before rollback. These are fixture-specific plans and buffer counts, not production latency or capacity guarantees. To see the report, run `python -m pytest -q -s tests/test_query_performance.py`.

From `frontend/`, `npm test` passed all **9 component checks** and `npm run build` passed. No frontend feature code or package pins changed on Day 12. Manual browser/UI checks and real Stripe verification remain pending. Day 13's broader end-to-end scenarios have not started.

## Files to read

| File | Purpose |
| --- | --- |
| `backend/app/security.py` | Atomic quotas, private keys, body limits and guarded API headers. |
| `backend/app/config.py` | Safe explicit origins and bounded settings. |
| `backend/app/main.py` | Middleware order, CORS and limiter cleanup. |
| `backend/app/auth.py` | Account quota after validated email normalization, before password work. |
| `backend/app/realtime.py` | Incoming live-message window. |
| `backend/alembic/versions/0009_query_indexes.py` | Reversible index changes. |
| `backend/app/drivers.py` and `rides.py` | Reuse coordinates already read with the offers. |
| `backend/tests/test_security.py` | Real Redis/API boundary checks. |
| `backend/tests/test_query_performance.py` | Synthetic plans and migration preservation. |

References: [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/), [Redis atomic Lua execution](https://redis.io/docs/latest/develop/programmability/eval-intro/), PostgreSQL 14 [multicolumn indexes](https://www.postgresql.org/docs/14/indexes-multicolumn.html) and [EXPLAIN](https://www.postgresql.org/docs/14/using-explain.html). Existing [database](DATABASE.md), [realtime](LIVE_UPDATES.md) and [payment](PAYMENTS.md) walkthroughs retain their feature-specific details.
