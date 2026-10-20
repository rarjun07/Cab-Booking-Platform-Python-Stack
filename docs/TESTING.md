# Day 7: first-week testing

For the later multiple-account HTTP/WebSocket/receipt-worker journeys and current full-suite commands, see [Day 13 testing](END_TO_END_TESTING.md). The results below record the original Day 7 checkpoint.

Day 7 checks the features from Days 1-6 together. It adds no ride-history, receipt, review, or wallet features. The user explicitly deferred Stripe setup and real payment verification on 2026-10-18; the Day 6 code commit `d2e9e778969be525ee5ff1a7983b1e185ffbf63d` was pushed and verified against GitHub before Day 7 started.

## Step 1: understand the connected test

`backend/tests/test_week_one_flow.py` follows one API journey rather than inserting an already-completed ride:

1. Register a rider, obtain a signed estimate, and request a ride. Retrying the same quote restores that ride instead of duplicating it.
2. Sign out, register a driver, save a vehicle, and go online near the pickup. The request appears in that driver's offers.
3. Accept the ride. The assigned driver becomes unavailable for other rides, and cannot read the rider's payment endpoint.
4. Reject an attempt to skip straight to completion. Advance through arriving, in progress, and completed; completion releases the driver for matching.
5. Sign out and log in as the rider again. Restore the completed trip, hide finished-trip driver location, and read payment readiness.
6. With Stripe settings absent, reject checkout with 503 without creating an invoice or setting a final fare. A sentinel payment adapter fails the test if checkout tries to contact Stripe.
7. Request another ride. The open request takes priority over the completed ride when restoring the account.
8. Sign out and replay the old session cookie. Protected account, ride, and payment reads must return 401.

This test uses the real PostgreSQL/PostGIS test schema and HTTP endpoints through FastAPI's TestClient. Only road-route metrics are replaced with fixed values, notifications are silenced, and Stripe is disabled. It is not a browser test or a real routing/payment-provider check. Existing realtime tests separately use real TCP WebSockets and Redis; existing payment tests use a controlled provider double and the official signature verifier.

## Step 2: run automated checks

Use the existing backend virtual environment:

```bash
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/backend"
source .venv/bin/activate
export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"
python -m pytest tests/test_week_one_flow.py -q
python -m pytest -q
python -m pip check
python -m alembic check
```

`pytest` checks expected behavior, `pip check` checks installed dependency compatibility, and `alembic check` detects model changes lacking a migration. The test fixture requires a separate PostgreSQL database whose name ends in `_test`; it refuses the development database. PostGIS must already be enabled by an administrator. See [DATABASE.md](DATABASE.md).

Since Day 8, the full suite also needs Pango/WeasyPrint and uses a local Celery subprocess/SMTP catcher for receipt tests. The library-path line above is for this Mac's Homebrew installation. See [HISTORY_RECEIPTS.md](HISTORY_RECEIPTS.md) for native dependencies and the full receipt walkthrough. These tests send no external email.

The journey test rolls back its accounts and rides. The concurrency/realtime suites create committed synthetic fixtures in the test database and remove them afterward. Redis tests use unique channel prefixes and do not flush Redis. They briefly bind local test servers and close them afterward. No test needs real Stripe keys.

Check React separately:

```bash
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/frontend"
npm run build
```

The build catches compilation and bundling problems; it does not prove that the rendered interface works.

## Step 3: manual browser walkthrough (pending)

Start the apps using [backend setup](../backend/README.md) and [frontend setup](../frontend/README.md), with PostgreSQL and Redis available. Use the normal browser window for the rider and a private window or separate browser profile for the driver. Two ordinary tabs share cookies and cannot keep different accounts signed in independently.

| Check | Action and expected result | Status |
| --- | --- | --- |
| Accounts and restoration | Register or sign in with each role. Reload each window; its own account returns. | Pending |
| Booking | Rider: **Use Delhi sample → Get fare estimate → Request this ride**. A saved requested ride appears. Public OSRM availability is required; do not assume the fixed test fare. | Pending |
| Driver setup and matching | Driver: **Save vehicle profile → Use Delhi sample location → Go online**. Online status and the nearby request appear; accept that request. | Pending |
| Live updates | Both windows show **Live updates connected**. Acceptance and each trip step update the rider without clicking Refresh. | Pending |
| Trip completion | Driver: **Head to pickup → Start trip → Complete trip**. Rider sees completed; driver has no active trip. | Pending |
| Deferred payment setup | Rider sees the local Stripe-configuration message and no usable checkout form. No payment is claimed successful. | Pending |
| Logout | Sign out in each window and reload. The account and its protected dashboard stay signed out. | Pending |

For location sharing, refresh the driver's location before its five-minute freshness window expires; only the assigned rider should see a fresh point during an active trip. See [LIVE_UPDATES.md](LIVE_UPDATES.md) for the full walkthrough and reconnect/manual-refresh checks.

These rows remain pending until the user actually tries them. Earlier browser automation was rejected by the URL policy; no workaround or new visual pass is claimed.

## Follow-ups carried forward

Observed on 2026-10-18: the connected journey passed individually, then all **145 backend tests passed** in 12.96 seconds. React build, pip consistency, and Alembic checks passed before Day 7's test/documentation-only changes. No application fix was required by these checks. These results do not mark the manual table or Stripe follow-up below as passed.

- **Stripe, deferred by user:** configure a sandbox and matching webhook listener, render the Payment Element, complete a real test-card success/decline/retry, and verify a Stripe-delivered signed webhook updates the correct invoice. Follow [PAYMENTS.md](PAYMENTS.md). Locally signed fixture events do not satisfy this check.
- **Browser checks, pending:** complete the table above, including the earlier Day 3-5 manual follow-ups. API tests and a successful build do not satisfy these checks.
- **Existing test warning:** FastAPI's TestClient emits a Starlette/HTTPX deprecation warning. Tests still run; dependency migration can be evaluated separately rather than changing the HTTP stack during this testing checkpoint.

Record observed results, remaining issues, and the Git checkpoint in [PROGRESS.md](PROGRESS.md). Do not call the whole payment integration verified while its deferred checks remain open.
