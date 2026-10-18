# Day 8: ride history and receipts

Day 8 adds private rider/driver history, downloadable completed-trip PDFs using the guide's WeasyPrint choice, and Celery email jobs over Redis. Day 7 documentation commit `f415d80e2dbeacfcd8c4666818a5e818e3276ea9` was verified equal to GitHub before starting. Stripe setup and real payment verification remain deferred by the user's decision.

## Step 1: understand history and the document

The **Ride history and trip documents** panel appears below your rider or driver dashboard. It lists only your completed/cancelled trips, five per UI page. Drivers see rides assigned to them; riders see rides they requested. The API permits 1-50 results per page and uses a stable creation-time/UUID cursor. Another account's cursor cannot expose its trips. Refresh history or let existing live updates reload the page after trip completion/payment changes.

For a completed ride, choose **Download PDF**. The document includes its reference, rider/driver names, request time, coordinates, route estimate, recorded fare and payment status. Cancelled or active rides cannot produce receipts. Names are escaped as text; the renderer cannot fetch images, stylesheets, fonts, URLs or local files from document content. System fonts are used.

A completed trip without verified payment produces a **Trip statement**, clearly marked as not proof of payment. A `succeeded` test-payment ledger entry produces a **Test payment receipt**. The invoice amount takes priority over a stored final fare or estimate. A missing final fare remains labeled estimated; downloading a PDF never changes payment/fare data. No completion timestamp is invented because the current ride model records request time only. All receipts describe this learning app's test payments.

Riders can open **View payment details** for an older completed ride. The existing checkout remains disabled until Stripe is configured. History does not bypass its payment ownership checks.

## Step 2: install and start the PDF-enabled backend

On macOS, WeasyPrint needs Pango. It has already been installed on this machine; install it when setting up another Mac:

```bash
brew install pango
```

From the backend:

```bash
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/backend"
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m alembic upgrade head
export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"
python -m uvicorn app.main:app --reload --ws-max-size 2048
```

The library path above is for this Apple Silicon Homebrew installation. Use your actual Homebrew library directory on another Mac. It must be set before Python starts and in each PDF/Celery/test terminal. Linux requires Pango/Harfbuzz system libraries instead; consult the linked WeasyPrint instructions. Missing native libraries produce a safe 503 on PDF download, not a fabricated receipt.

Migration `0006_receipt_emails` creates only the email-request table and indexes. It preserves existing accounts, sessions, rides and payments. Do not initialize tables with `create_all`.

React, in another terminal:

```bash
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/frontend"
npm ci
npm run dev
```

Keep the existing PostgreSQL and Redis services running. Sign in at <http://127.0.0.1:5173/> and complete a sample trip if your account has no history yet.

## Step 3: test email locally without an email provider

Email is disabled by default. PDF download works independently. The following setup uses a catcher bound to `127.0.0.1:1025`; it saves messages locally and never forwards them to the internet. No paid account or real SMTP credentials are needed.

In a separate backend terminal with the virtual environment active, start the catcher:

```bash
python -m scripts.mail_catcher
```

Messages are saved as owner-only `.eml` files in ignored `tmp/mail/`. Open one in a mail viewer to inspect its PDF attachment. The catcher prints filenames only, not message bodies or addresses. Stop it with Ctrl+C when finished. The catcher requires the development dependencies.

Start a worker in another backend terminal:

```bash
source .venv/bin/activate
export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"
RECEIPT_EMAIL_ENABLED=true SMTP_STARTTLS=false python -m celery -A app.tasks:celery_app worker --pool=solo --concurrency=1 --loglevel=WARNING --without-gossip --without-mingle --without-heartbeat
```

`--pool=solo` is the simple local development worker configuration. The Redis broker defaults to the existing `REDIS_URL`; queue keys use `cab_booking:tasks:v1:` so they are separate from realtime channels. Only job UUIDs go into task arguments. PDF content, receipt snapshots, and addresses are not put in task arguments or result storage.

Restart the backend terminal with the same local email flags:

```bash
RECEIPT_EMAIL_ENABLED=true SMTP_STARTTLS=false python -m uvicorn app.main:app --reload --ws-max-size 2048
```

These process-only flags leave the ignored `.env` unchanged. Defaults use SMTP host `127.0.0.1`, port `1025`, and sender `receipts@example.com`. If your private `.env` overrides SMTP settings, explicitly set the matching local values for both processes; do not point this test at a real mail provider. The optional settings are documented in `backend/.env.example`.

As the signed-in account, click **Email to my account**, then **Check email status**. `queued` means saved/awaiting a worker or retry, `sent` means the SMTP server accepted the message, and `failed` means configuration/delivery needs attention. For this setup, sent means captured locally, not delivered to an internet inbox. The destination is always the requesting account's server-stored email; the API accepts no alternate destination.

## Step 4: understand background work and retries

FastAPI saves a receipt snapshot and job in PostgreSQL before publishing to Redis. Its document fingerprint is computed from server data. Repeated requests for the same document/account reuse that job; an updated payment state creates a new document version. A sent job is returned without publishing again. If publication fails, the API returns 503 but keeps the job; retrying the button republishes that same saved job. There is no automatic database sweep for broker-lost jobs at this milestone: request the receipt again after restoring the broker/worker.

The worker opens its own database session, locks the job, generates the attachment with WeasyPrint, and submits it to SMTP with a ten-second network timeout. Duplicate tasks serialize and skip already-sent jobs. Failures have at most three delivery attempts with bounded Celery backoff; a failed job can be manually reset after a one-minute cooldown. If configuration is disabled, the worker marks the job failed. No raw SMTP diagnostic is stored or returned.

SMTP and PostgreSQL do not share a transaction. A worker crash after SMTP acceptance but before the database commit can cause a resend on retry. A stable Message-ID identifies the job, but it does not guarantee recipient-side deduplication. Stored status is an observed SMTP submission result, not inbox confirmation. The attachment is the snapshot captured when requested; download a new PDF or request the changed document version after payment updates.

Remote SMTP requires STARTTLS and matching username/password settings, kept only in private configuration. Actual external delivery is not configured or verified in this checkpoint; use your chosen provider and request delivery deliberately when ready.

## API and files

| Endpoint | Behavior |
| --- | --- |
| `GET /api/rides/history?limit=10&cursor=<last-ride-uuid>` | Terminal rides belonging to the authenticated participant, with `items` and `next_cursor`. |
| `GET /api/rides/{id}/receipt.pdf` | Participant-only completed-trip PDF attachment; private/no-store. |
| `GET /api/receipts/config` | Whether local email requests are enabled; no credentials exposed. |
| `POST /api/rides/{id}/receipt-email` with `{}` | Allowed Origin and authenticated participant required; 202 for queued requests, 200 for a previously sent document. |
| `GET /api/rides/{id}/receipt-email` | Current document/account's job status or null; no arbitrary job-ID lookup. |

| File | Purpose |
| --- | --- |
| `backend/app/history.py` | Ownership, pagination, downloads, document deduplication, and queue submission. |
| `backend/app/receipts.py` | Server-owned snapshot, escaped HTML, offline-only PDF rendering. |
| `backend/app/tasks.py` | Celery configuration, worker row locks, bounded retries, PDF attachment, and SMTP submission. |
| `backend/alembic/versions/0006_receipt_emails.py` | Durable versioned requests and delivery status. |
| `backend/scripts/mail_catcher.py` | Loopback-only development catcher, never an email relay. |
| `frontend/src/RideHistory.jsx` | Private paginated history, downloads, email requests/status, and older-ride payment access. |
| `backend/tests/test_history_receipts.py` | History/privacy/cursor/PDF/job/failure checks. |
| `backend/tests/test_receipt_worker.py` | Real Celery subprocess, namespaced Redis, and local SMTP end-to-end delivery. |

## Observed verification

- **157 backend tests passed**, including 12 new history/PDF/email checks. The real worker test submits through the API, publishes duplicate copies over Redis, captures one PDF email on loopback SMTP, and reads `sent` with one attempt from PostgreSQL. Synthetic committed fixtures and only that test's unique Redis keys are cleaned up.
- PDF extraction verifies content, amount/payment labels and escaped names. The generated unpaid sample was rendered with Poppler and visually inspected as one readable page without clipping or overlap.
- React production build passed. Alembic migration applied; drift check and pip consistency passed. Existing database-preservation and full upgrade/downgrade tests passed at the new head. One existing TestClient/HTTPX deprecation warning remains.
- Browser interaction with the new React panel is unverified because the earlier URL-policy rejection remains in effect. Manual follow-up: complete/reload a trip, page history, download/open a PDF, use the local catcher, and verify account separation/sign-out. Prior Day 3-5 browser checks remain pending.
- Stripe setup, real test transaction and Stripe-delivered webhook/rendered checkout remain deferred. No real email was sent to an external SMTP provider. Email stays disabled in the ordinary local configuration until explicitly enabled.

References: [WeasyPrint setup and native libraries](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html), [WeasyPrint Python API](https://doc.courtbouillon.org/weasyprint/stable/api_reference.html), [Celery Redis broker](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html), [Celery tasks and retries](https://docs.celeryq.dev/en/stable/userguide/tasks.html).
