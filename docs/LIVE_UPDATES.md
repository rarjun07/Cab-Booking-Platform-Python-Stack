# Day 5: live ride and driver location updates

The user chose to include this optional milestone. FastAPI WebSockets now deliver ride, matching, and driver-location notifications through Redis. React refreshes authorized API data automatically and reconnects after a lost connection. Refresh buttons remain available when realtime is unavailable.

PostgreSQL remains the source of truth for rides, locations, declines, and sessions. Redis carries short-lived notifications; it does not store ride records or replace the database. No new schema migration is needed: the Day 4 schema already supports location timestamps and trip statuses.

## Start the services

This Mac already has Redis 8.6.0 listening locally on port 6379. We reused it without restarting it, changing its configuration, or changing other projects' keys. Check it with:

```bash
redis-cli ping
```

Expected output: `PONG`. On another development machine, install Redis and run a loopback-only service first. For example, with Redis installed and port 6379 free, use a separate terminal:

```bash
redis-server --bind 127.0.0.1 --port 6379 --protected-mode yes --save '' --appendonly no
```

This foreground command disables disk persistence for the local notification demo. Reuse an existing server rather than starting a competing one. Keep deployed Redis private and use appropriate authentication/TLS; the local loopback example is not a deployment configuration.

Backend terminal:

```bash
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/backend"
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --ws-max-size 2048
```

The dependencies now include `redis==8.1.0` and `websockets==17.2`. Installation is needed only when dependencies are missing or have changed. If an older backend is already running, stop it in its terminal and restart with the command above to apply the transport frame limit. The application also rejects text messages larger than 2 KiB.

Frontend terminal:

```bash
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/frontend"
npm run dev
```

Open <http://127.0.0.1:5173/> and sign in. The message below the account panel should become **Live updates connected** only after the server has authenticated the connection and subscribed to Redis. It may show a reconnecting message when a service is unavailable.

## Try the live two-account flow

Use separate browser profiles or a normal and private window so rider and driver have independent cookies. Two tabs in the same profile share the account. The temporary automated API demo accounts use random passwords and are not intended as manual login accounts; create your own demo accounts.

1. In the driver window, create/sign in to a **Driver** account, save vehicle details, choose **Use Delhi sample location**, and click **Go online**.
2. In the rider window, create/sign in to a **Rider** account. Choose **Use Delhi sample → Get fare estimate → Request this ride**.
3. The driver's nearby-request list should update automatically. Click **Accept ride**. The rider should see `accepted` and the assigned driver reference without clicking Refresh.
4. In the driver's location form, enter latitude `28.6150` and longitude `77.2100`. Wait at least one second after the preceding location update, then click **Share updated location**. When connected this message travels over the WebSocket; otherwise the button uses the authorized HTTP location endpoint.
5. The rider's **Driver's last shared location** should update. Only the rider assigned to that active ride can read these coordinates. Offline, stale, unassigned, and completed rides do not expose a fresh point.
6. Use the driver's buttons in order: **Head to pickup → Start trip → Complete trip**. The rider should see `arriving`, `in_progress`, then `completed`. Drivers cannot skip or reverse steps, and only the assigned driver can change them.
7. Completion releases the driver's active assignment so another request can be accepted. It does not charge a payment or set a final billed fare; Stripe remains Day 6 work.
8. Choose **Go offline** when done. Signing out revokes the session and closes its live connection, but availability remains the explicitly saved online/offline setting.

Location sharing is manual for this milestone. It does not request GPS permission or track the device automatically. Locations expire after five minutes by default. **Refresh location / go online** submits a fresh point; reading the dashboard does not renew freshness.

## How the connection works

```text
REST/driver WebSocket write -> PostgreSQL commit
                           -> Redis notification
                           -> authorized account WebSocket
                           -> React reads current data from protected REST endpoints
```

Each connection subscribes only to its own server-selected account channel and a generic matching-invalidation channel. The client cannot choose a Redis channel or impersonate another user. Account notifications contain an event type and, where needed, a ride ID. The shared matching notification contains only `{"type":"matching.changed"}`: no ride IDs, locations, email addresses, or tokens.

The server checks the session cookie, signed JWT, database session, role, account ID, and exact allowed Origin before accepting a connection. It rechecks authentication before forwarding broker events or handling messages and at least every two seconds by default while idle. Expired/revoked accepted connections close with code `4401`.

WebSocket routes live under `/api/ws/` so the existing HTTP-only cookie with path `/api` is sent. No token is placed in a URL or localStorage. Vite forwards `/api` WebSocket upgrades with `ws: true` and preserves the browser Origin. A future deployment must also proxy upgrades and use HTTPS/WSS.

## Endpoints and messages

| Endpoint | Purpose |
| --- | --- |
| `WS /api/ws/rider/{user_id}` | Rider notifications; account must match the signed-in rider. |
| `WS /api/ws/driver/{user_id}` | Driver notifications and manual location messages; account must match the signed-in driver. |
| `POST /api/drivers/me/location` | HTTP fallback with `{"location":{"latitude":28.615,"longitude":77.210}}`. Requires an online driver and allowed Origin. |
| `GET /api/rides/{ride_id}/driver-location` | Owning rider's assigned driver point/timestamp; returns null for an unassigned or finished ride and a null point if offline/stale. |
| `POST /api/drivers/me/rides/{ride_id}/status` | Assigned driver's next step, e.g. `{"status":"arriving"}`. Requires an allowed Origin. |

Driver WebSocket location message:

```json
{"type":"location.update","request_id":"<new UUID>","location":{"latitude":28.615,"longitude":77.210}}
```

Successful writes receive `location.saved` with the same request ID and an update timestamp. Validation/business-rule errors return a safe `error` message without echoing submitted data. Rider connections are read-only apart from `{"type":"ping"}`; valid pings receive `pong`. Binary frames are rejected with 1003 and oversized messages with 1009.

Location writes require an online profile and allow one update per second through the dedicated HTTP/WebSocket location paths, using the locked driver's stored timestamp. General API/connection rate limits remain Day 12 work; this is not a claim of deployment-wide abuse protection.

## Failure and recovery

Redis Pub/Sub does not retain missed messages. A reconnect sends `ready`, and the server sends a `sync` signal every 15 seconds by default; React then rereads authorized PostgreSQL state. Event refreshes are coalesced and do not overwrite unsaved vehicle/location inputs. Completed rides remain visible to the rider in the current page, while the driver's active assignment is cleared.

Redis publication happens after the database commit. If publishing fails, the saved API operation still succeeds; a safe warning is logged and live connections close/retry when their broker connection fails. React retries connections with delays up to 15 seconds, keeps manual Refresh controls, and times out unconfirmed location messages. Database sessions are short and are not held open for the lifetime of a socket. Slow sends are bounded, subscriptions/tasks are cleaned up on disconnect, and clients reject pending acknowledgements when their connection closes.

The default channel prefix is `cab_booking:realtime:v1`. Redis Pub/Sub channels are global across Redis logical databases; the prefix, not the `/0` database number, separates this project. Multiple backend workers must share the Redis URL and prefix. Tests use unique `cab_booking:test:<UUID>` prefixes and do not flush Redis or change unrelated keys.

Optional settings are documented in `backend/.env.example`: `REDIS_URL`, `REALTIME_CHANNEL_PREFIX`, `WEBSOCKET_SESSION_CHECK_SECONDS=2`, and `WEBSOCKET_SYNC_SECONDS=15`. Local defaults work without new secrets. Restart FastAPI after changing configuration.

## Verification evidence

- **113 backend tests passed**, including real local TCP WebSocket servers, real Redis channels, and the guarded PostgreSQL `_test` database. Synthetic committed test fixtures are removed afterward.
- Checks cover Origin/account/role/token rejection; account isolation; accept/status delivery; location privacy, validation, freshness, and throttling; idle logout and JWT expiry; invalid/oversized messages; Redis outage; reconnect recovery; and coherent location reads during a concurrent offline update.
- Alembic reports no drift; the current schema revision remains `0004_driver_matching`. Pip dependency check and React production build passed.
- Live development demo passed through Vite's WebSocket proxy and two independent backend processes: REST writes on 8000 reached a rider socket on 8002 through Redis. Driver location, trip progression to completed, hidden completed-trip location, and closure after logout all passed. Demo ride `77e46024-c667-4715-8090-10bc73ada350` is completed; its synthetic driver was left offline. Synthetic accounts/ride remain local development test data.
- Frontend HTTP availability passed. Automated visual interaction remains unverified after the earlier browser URL-policy rejection. The user reported that they have not tried the manual **Live updates connected** check yet. API/protocol checks and a build are not claimed as browser UI verification.

References: [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/), [redis-py async cleanup and subscriptions](https://redis.io/docs/latest/develop/clients/redis-py/async/), and [Redis Pub/Sub delivery behavior](https://redis.io/docs/latest/develop/pubsub/).

Day 6 follow-up: [test checkout](PAYMENTS.md) now uses `payment.changed` notifications for the owning rider and restores the latest completed ride when no open ride exists. The Day 5 evidence above remains historical; real payment-provider verification is still pending.
