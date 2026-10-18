# FastAPI backend

The original health endpoint below is now joined by PostgreSQL-backed registration, login, session verification, and logout. See [the authentication walkthrough](../docs/AUTHENTICATION.md) for database setup, the new files, and tests.

Day 2 adds the booking models, PostGIS, and Alembic migrations. Follow [the database walkthrough](../docs/DATABASE.md) to enable PostGIS, apply migrations, and inspect the schema. Database initialization is now handled by `python -m alembic upgrade head`.

Day 3 adds authenticated fare estimates and ride requests with OSRM road routing. Follow [the ride-booking walkthrough](../docs/RIDE_BOOKING.md) for the pricing formula, signed quotes, API endpoints, and sample route. Apply migration `0003_ride_quote` before using these endpoints.

Day 4 adds driver profiles, availability, nearby requests, accept/decline matching, and open-ride recovery. Follow [the matching walkthrough](../docs/RIDE_MATCHING.md). Run `python -m alembic upgrade head` to apply `0004_driver_matching` before using the new endpoints.

Day 5 adds cookie-authenticated FastAPI WebSockets and Redis notifications, manual driver location sharing, and authorized trip progression. Follow [the realtime walkthrough](../docs/LIVE_UPDATES.md) for Redis startup, protocol/security details, and the two-window demo. No additional schema migration is needed. The complete test suite now also requires a running local Redis service.

Day 6 adds Stripe test PaymentIntents and verified payment webhooks. Apply migration `0005_test_payments` and follow [the payment setup walkthrough](../docs/PAYMENTS.md) to configure private test keys and the listener. `python -m scripts.configure_test_payments` saves entered test keys without echoing them. Without configuration, checkout stays disabled; real Stripe provider verification is pending.

Day 8 adds account-owned history, WeasyPrint PDF documents and Celery receipt-email jobs. Apply `0006_receipt_emails` and follow [the history/receipt walkthrough](../docs/HISTORY_RECEIPTS.md). On this Mac, install Pango and set `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` before starting Python. PDF download works with email disabled; the walkthrough shows a free local mail catcher and worker.

Day 9 adds completed-trip reviews for the rider and assigned driver, strict 1-5 ratings, private feedback, idempotent submissions and concurrency-safe rating aggregation. Apply `0007_review_timestamps`; no new dependency or service is needed. See [ratings and reviews](../docs/REVIEWS.md) for eligibility, locking, API payloads and the two-account walkthrough.

## What we added

- `.venv/`: this project's isolated Python environment. It holds installed libraries locally and is ignored by Git.
- `app/__init__.py`: marks `app` as a Python package.
- `app/main.py`: creates the FastAPI application and defines its first endpoint.
- `requirements.txt`: records the installed dependency versions so another developer can reproduce the environment.

FastAPI defines the API. Uvicorn runs it as a local web server.

## Set up on another machine

Use Python 3.14 for the environment verified at this checkpoint. From the project root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run locally

From the project root:

```bash
cd backend
source .venv/bin/activate
export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"
python -m uvicorn app.main:app --reload --ws-max-size 2048
```

If your terminal is already inside `backend/`, skip `cd backend`.

- Health endpoint: <http://127.0.0.1:8000/api/health>
- Interactive API documentation: <http://127.0.0.1:8000/docs>

The health endpoint should return:

```json
{"status":"ok"}
```

Press `Ctrl+C` to stop the server. Run `deactivate` to leave the virtual environment.

## Understand the code

1. `from fastapi import FastAPI` imports the framework's application class.
2. `app = FastAPI(...)` creates our API application.
3. `@app.get("/api/health")` registers a URL that accepts HTTP GET requests.
4. `health_check()` runs when someone requests that URL.
5. The returned Python dictionary is sent as JSON.

In the startup command, `app.main:app` means "import the `app` object from `app/main.py`." `--reload` restarts the development server when you change Python code.

The root URL `/` returns 404; use `/docs` to explore the API or open the React app for the user interface.

## Scope of this checkpoint

The health endpoint checks API availability only. Custom authentication uses PostgreSQL user/session tables. Day 2 adds PostGIS and the driver, ride, payment, and review models through Alembic. Day 3 implements estimates, ride creation, and owned ride status; Day 4 adds driver availability and matching; Day 5 adds realtime and trip progression. Day 6 payment code is tested locally but awaits real Stripe sandbox verification. Reviews remain later work. See the progress log for verification and Git checkpoints.

Reference: [FastAPI's official first-steps tutorial](https://fastapi.tiangolo.com/tutorial/first-steps/).
