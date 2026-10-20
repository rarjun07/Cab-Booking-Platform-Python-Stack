# Day 13: multiple-account API journeys

Day 13 connects the implemented features through a real local HTTP server. Separate riders and drivers register through the API, carry their own cookies, request and complete trips, and exercise the later payment/review/wallet/receipt paths. Two concurrent HTTP scenarios check competing assignments. This milestone also fixes a fare-estimate quota classification error exposed by its regression test.

These are API/service journeys. The React tests run separately in jsdom. Actual browser/mobile/zoom/screen-reader checks remain pending, and the user's actual Stripe setup/transaction/rendered-checkout checks remain deferred. A locally signed fixture notification is not a Stripe-delivered event.

## Step 1: prepare the existing services

Use the existing backend environment, dedicated PostgreSQL `_test` database with administrator-enabled PostGIS, and local Redis. The test fixture refuses the development database and initializes the schema through Alembic. No new dependency, migration or paid account is needed.

From the backend terminal:

```bash
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/backend"
source .venv/bin/activate
export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"
python -m pytest -q tests/test_end_to_end.py tests/test_security.py::test_actual_get_estimates_are_limited_before_route_parsing
```

You do not need to start your normal API/frontend server or configure real Stripe keys for these checks. The fixtures reserve temporary loopback ports and start only the services they own. Existing development servers, PostgreSQL and Redis are left running. Run the suite serially; the tests temporarily override the shared FastAPI application's dependencies/configuration and are not configured for parallel pytest workers.

## Step 2: understand what is exercised

| Part | How it runs |
| --- | --- |
| HTTP, sessions and request protection | Real Uvicorn on a reserved loopback socket, HTTPX clients with separate cookie jars, real authentication/Origin/role/ownership checks, default Redis quotas. |
| PostgreSQL/PostGIS | Real migrated `_test` database; new sessions per HTTP request and actual transaction/assignment locks. |
| Realtime | Real TCP WebSockets and Redis Pub/Sub, private notification reads and session-revocation closure. |
| Routing | Controlled valid route metrics; no public OSRM call or availability claim. |
| Payments | Controlled PaymentIntent create/retrieve responses and locally signed fixtures through the actual webhook endpoint and Stripe SDK signature verification. No Stripe network call or charge. |
| PDF and email | Real WeasyPrint PDF generation, Redis task transport, a separate Celery worker and loopback SMTP catcher; no external email sent or inbox delivery claim. |
| React | Separate simulated-DOM interaction checks with controlled HTTP fixtures; no browser automation or real layout measurements. |

`backend/tests/journey_support.py` owns the setup and cleanup. It registers accounts with a unique run suffix, creates a unique promo and Redis namespace, starts the temporary server, and can start the local worker/catcher. Teardown closes clients/sockets, stops owned processes, deletes only its Redis prefix and removes only its associated test records in foreign-key order. The development database and ignored configuration are unchanged.

## Step 3: follow the main journey

`test_two_rider_driver_journeys_with_receipt_email_promos_reviews_wallet_and_revocation` performs the following:

1. Register two riders, two drivers and an unrelated account with separate cookie jars. Save vehicles and go online through the driver API.
2. Request two rides using signed quotes. Retrying the first quote returns the existing UUID. Both available drivers initially see both nearby offers.
3. Assign each driver a different ride; the first driver cannot also accept the second. Reject another driver's progression request and an attempt to skip trip steps. The assigned rider can read the driver's fresh point.
4. Complete the first trip and confirm its location becomes unavailable. That driver can accept and complete a third request while the second driver is still occupied. The second driver then completes their trip independently.
5. Apply one promo to each of the first two completed rides. The controlled INR 104.38 fare becomes INR 93.94 after an INR 10.44 discount. Identical promo and checkout retries reuse their saved records.
6. Report controlled provider success without changing the local pending payment. Deliver a signed fixture event, verify saved success, and replay the same event without duplicating it.
7. Submit both participants' reviews for the first two trips and check the four independent rating summaries. Page the first rider's two trips and verify the other participants see only their own history.
8. Deny the unrelated account and other rider access to the first trip's status, location, payment, promo, reviews, PDF and email status.
9. Generate a paid-discount PDF. Queue the same email request twice, receive the PDF through the real local worker/SMTP catcher, and verify the owned saved request reaches sent with one attempt. The document uses the correct trip, recipient and discounted amount.
10. Retry an INR 100 wallet top-up with one request UUID. Provider success alone leaves the balance at zero; signed fixture deliveries create one credit. The other rider's wallet stays zero and cannot read the top-up. The owner receives a private wallet notification.
11. Revoke the first rider's session, reject replay of the old cookie and close the existing socket with the application's 4401 expired/revoked-session code. The second rider stays signed in.

The fixture uses a valid code stored only in the test database. It does not renew the development `WELCOME10` code or add a synthetic development wallet balance. Tests assert scoped record counts rather than assuming every table belongs to the current journey.

## Step 4: check competing and ineligible drivers

Two barrier-started HTTP requests exercise each race with separate request/database sessions:

- Two drivers attempt to accept one ride: one succeeds and the other receives 409.
- One driver attempts to accept two rides: one succeeds and the other receives 409.

The resulting ride reads and stored rows must show exactly one accepted assignment for the scenario. Existing direct database concurrency tests remain in the full suite as additional coverage.

A separate journey checks a nearby fresh driver, an out-of-range driver and an expired-location driver. Only the eligible driver appears in candidates. Far/stale accepts return 409; after the nearby driver declines, that driver cannot accept it either. The rider's request remains requested.

## Step 5: understand the regression fix

The real fare-estimate endpoint is **GET `/api/rides/estimate`**. Day 12 placed its special quota inside a write-method branch. The new regression registered a real rider and sent 21 malformed-coordinate GET requests: before the fix, all reached route parsing and returned 422 instead of the last being throttled.

`app/security.py` now classifies estimate requests outside the write-only branch. The first twenty requests may reach parsing, while the twenty-first returns 429 and Retry-After before route processing. The regression uses real isolated Redis keys and invalid coordinates, so it contacts no routing provider. All other configured quota behavior remains covered by the security suite.

## Step 6: run the complete checks

From `backend/`, with the same environment/library path:

```bash
python -m pytest -q
python -m pip check
python -m alembic check
```

From `frontend/`:

```bash
npm test
npm run build
```

`frontend/tests/booking-flow.test.jsx` adds two component journeys. One uses the Delhi sample, obtains a quote, loses a booking response, retries the same signed quote, restores the completed ride and shows its promo/disabled-checkout controls. The other preserves route inputs after a controlled 429 and notifies the account owner after a later 401. No price is submitted during booking retries.

Focused backend journey/GET-regression checks passed **5 tests in 7.30 seconds** after correcting the test's expected logout close code to match the existing 4401 protocol. The final complete backend suite passed **268 tests in 33.27 seconds**, with the existing TestClient/HTTPX deprecation warning. React passed **11 checks**, and its production build passed. Dependency consistency and Alembic no-drift checks passed; the schema remains `0009_query_indexes`. Git evidence is recorded in [PROGRESS.md](PROGRESS.md).

## Pending checks and next milestone

The [manual UI checklist](UI_POLISH.md) and [Stripe setup/real-provider checks](PAYMENTS.md) remain pending with their existing status. Service tests and simulated DOM interactions do not verify browser rendering, Stripe's account/API behavior or external mailbox delivery.

Day 14 covers Docker, Compose and deployment after Day 13's reviewed commit, push and exact remote verification. No container or public deployment is included in this milestone. Existing [first-week testing](TESTING.md), [request protection](SECURITY_PERFORMANCE.md) and [receipt setup](HISTORY_RECEIPTS.md) documents explain the underlying checks and service limitations.
