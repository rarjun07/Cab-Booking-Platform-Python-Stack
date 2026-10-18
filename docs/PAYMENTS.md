# Day 6: Stripe test payments

Day 6 adds PaymentIntents, a React Payment Element, and verified Stripe webhooks. The mentor guide specifically schedules PaymentIntents, so this implementation uses them. All payment credentials must be from a Stripe sandbox/test environment; live API keys are rejected by application configuration.

**Current checkpoint:** code and local automated checks are ready, but no real Stripe sandbox transaction or Stripe-delivered webhook has been verified. Test keys and a webhook listener are still needed. On 2026-10-18, the user explicitly deferred this setup and rendered/provider verification to continue to Day 7 after the Day 6 code Git checkpoint. These checks remain outstanding.

## Understand the flow

1. A driver completes the trip using the existing trip controls.
2. The owning rider clicks **Open test checkout**.
3. FastAPI creates one local payment record and freezes its INR amount from the ride's stored final fare, or its stored estimate if no final fare exists. The browser cannot submit an amount, currency, rider ID, or payment status.
4. FastAPI creates or reuses that payment's Stripe PaymentIntent. The local payment UUID supplies a stable idempotency key.
5. Stripe's Payment Element collects the test card details directly. Our React app uses Stripe.js to confirm the test payment; our backend never receives card numbers or CVCs.
6. Stripe sends a signed webhook to FastAPI. The server verifies the raw body/signature, retrieves Stripe's current PaymentIntent, checks the invoice relationship and amount, then updates PostgreSQL.
7. The rider sees payment status through the protected API and existing live updates. Browser-side confirmation alone never marks the invoice paid.

Trip completion and payment are separate states: a completed ride remains completed if a card fails. A successful payment records `status=succeeded` and `paid_at`; it does not fabricate a second trip-completion event.

## Step 1: obtain a Stripe test environment

Use your own Stripe sandbox/test account if you have one. Open [Stripe's sandbox dashboard](https://dashboard.stripe.com/sandboxes), then the API keys for that environment. You need the matching publishable and secret keys:

- `pk_test_...`: publishable key; used by Stripe.js.
- `sk_test_...`: secret key; backend only.

Do not paste secret keys into chat or commit them. Do not use real card details. Account access varies; if Stripe setup is unavailable, keep the provider verification pending rather than claiming a mocked test is a Stripe transaction.

Stripe also documents temporary claimable sandboxes through its CLI. Creating one sends your chosen identity information to Stripe and creates an external test environment. We have requested the user's setup preference; no sandbox has been created and no name/email has been sent for provisioning. Only proceed after the user chooses that option. Do not substitute another country or someone else's account to bypass signup requirements.

## Step 2: run the local webhook listener

Install the official Stripe CLI if it is not already installed. For macOS with Homebrew:

```bash
brew install stripe
stripe login
```

Follow the CLI's own sign-in instructions for your test environment. Leave a third terminal running:

```bash
stripe listen --events payment_intent.succeeded,payment_intent.processing,payment_intent.payment_failed,payment_intent.canceled --forward-to http://127.0.0.1:8000/api/webhooks/stripe
```

The listener displays a signing secret starting with `whsec_`. It belongs to this listener; use it rather than a secret from a different Dashboard endpoint. Keep the listener running while testing. The application webhook is public to Stripe and authenticates the signature, so it does not require a browser cookie or Origin header.

`stripe trigger payment_intent.succeeded` creates an unrelated Stripe fixture. Our webhook intentionally ignores PaymentIntents that are not linked to this project's local invoice, so that command alone does not verify the cab-payment flow.

## Step 3: save test credentials locally

From your own terminal, with the backend environment active:

```bash
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/backend"
source .venv/bin/activate
python -m scripts.configure_test_payments
```

Enter the test secret key, matching test publishable key, and listener signing secret at the hidden prompts. The helper checks prefixes, asks before replacing existing Stripe entries, preserves the other configuration, and atomically saves ignored `backend/.env` with owner-only permissions. It does not print key values. Alternatively edit those three settings directly in your private `.env`:

```dotenv
STRIPE_SECRET_KEY=sk_test_YOUR_SANDBOX_VALUE
STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_SANDBOX_VALUE
STRIPE_WEBHOOK_SECRET=whsec_YOUR_LISTENER_VALUE
```

The block above contains placeholders, not usable keys. Safe commented examples are in `backend/.env.example`. There are no frontend `VITE_` secret variables; the backend returns only a test publishable key and an owner-only checkout client secret. Missing configuration keeps checkout disabled and returns an explanatory 503 instead of fake success.

## Step 4: run both applications

Backend:

```bash
python -m pip install -r requirements-dev.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --no-proxy-headers --ws-max-size 2048
```

Restart FastAPI after configuring keys; settings are cached. Keep PostgreSQL and Redis running as documented for earlier days. The new dependencies include `stripe==16.0.0`, `@stripe/react-stripe-js==7.0.0`, and `@stripe/stripe-js==10.1.0`.

React, in another terminal:

```bash
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/frontend"
npm ci
npm run dev
```

## Step 5: verify a real Stripe test payment

1. Open <http://127.0.0.1:5173/>. Use independent browser profiles/windows for the rider and driver, following the Day 5 walkthrough.
2. Create a sample ride, accept it as a driver, then use **Head to pickup → Start trip → Complete trip**.
3. As its rider, open the completed trip's **Stripe test payment** card and click **Open test checkout**. The server freezes the stored estimate as this demo's final invoice when no final fare is already recorded.
4. In Stripe's embedded form use the test Visa `4242 4242 4242 4242`, a future expiry such as `12/34`, and any three-digit CVC. Use only Stripe's documented test values.
5. Click the test-payment button. A successful Stripe.js response can show **Waiting for the signed payment notification** while the listener forwards the webhook.
6. Confirm that the listener reports a successful response, the test PaymentIntent is successful in Stripe, and this app shows **Test payment received** with invoice status `succeeded`. Refresh payment status if realtime is disconnected.
7. Reload the page. The rider's latest open ride is restored first; if none exists, the latest completed ride is restored so its payment can be reopened. This is not a full ride history list; older invoices remain accessible by their owned ride references through the API until Day 8 adds history.

Then try a failed payment on a separate unpaid invoice with Stripe's generic-decline card `4000 0000 0000 0002`. The invoice must not become succeeded. Retry using the successful test card; the same invoice and PaymentIntent are reused. Repeated checkout requests/webhook deliveries must not create duplicate payments or advance `paid_at` twice.

Never share or log the checkout client secret, place it in a URL, or persist it in browser storage. Stripe.js is loaded only when checkout opens. HTTPS is required for a deployed payment page; local HTTP is for development.

## Endpoints and database changes

| Endpoint | Purpose |
| --- | --- |
| `GET /api/payments/config` | Authenticated rider reads test-checkout readiness and the public test key only. |
| `GET /api/rides/{ride_id}/payment` | Owning rider reads the local invoice; returns null before one exists. |
| `POST /api/rides/{ride_id}/payment-intent` with `{}` | Owning rider prepares checkout for a completed trip. Requires an allowed Origin. Extra fields are rejected. |
| `POST /api/webhooks/stripe` | Raw-body signed Stripe event; no user session or browser Origin required. |

Migration `0005_test_payments` adds INR currency, creation/paid timestamps, and `payment_events` keyed by Stripe event ID. Existing payment amounts, status, and provider IDs are retained. Existing rows receive a currency/creation default; old payment timestamps are not invented. Event audit records store IDs/types/relationships, not raw webhook payloads or client secrets.

The one-payment-per-ride constraint plus ride/payment row locks serialize competing requests. PaymentIntent creation uses a durable UUID even if Stripe times out before linking an ID. If an invoice is still unlinked after 23 hours, the API refuses automatic recreation: Stripe can prune idempotency keys after 24 hours, so manual reconciliation is required before proceeding. Linked intents are retrieved and reused rather than replaced. Cancelled/refunded invoices cannot open another checkout.

Webhook handling verifies the SDK signature with a five-minute tolerance and a 256 KiB body limit. It rejects live/connected-account events and checks the retrieved object's ID, test mode, currency, amount, project/payment/ride/rider metadata, and received amount on success. Current state is retrieved under the payment lock so out-of-order deliveries do not blindly replay stale state. Processed event IDs are recorded atomically with the status update. Succeeded/closed invoices do not regress to pending on a late event. A provider failure returns a retryable error without falsely recording the event as processed.

Refund creation/reconciliation, saved cards, off-session charging, marketplace transfers, and wallet top-ups are outside this day's scope. Generic rate limiting remains scheduled for Day 12.

## Files to understand

| File | Purpose |
| --- | --- |
| `backend/app/payment_gateway.py` | Official Stripe SDK adapter, timeout/retry bounds, stable idempotency key, and safe errors. SDK objects become dictionaries at this boundary. |
| `backend/app/payments.py` | Invoice ownership, stored-fare checkout, signature verification, canonical state validation, and duplicate-event handling. |
| `backend/app/payment_schemas.py` | Empty checkout input and safe public payment/checkout responses. |
| `backend/alembic/versions/0005_test_payments.py` | Versioned payment audit/currency fields and event table. |
| `backend/scripts/configure_test_payments.py` | Hidden local credential prompts; not run automatically. |
| `frontend/src/RidePayment.jsx` | Lazy Stripe.js loading, Payment Element, confirmation, status display, and manual refresh. |
| `backend/tests/test_payments.py` | Payment access, signing/validation, duplicate/order/failure behavior, SDK conversion, and real PostgreSQL concurrency. |

## Observed verification

- **144 backend tests passed**, including existing authentication, PostGIS, matching, realtime, and new payment checks. Payment-provider API calls are controlled test doubles; webhook signatures use the official SDK and a local fixture signing secret.
- Separate-connection tests verify one invoice/intent under concurrent checkout attempts and one recorded success under duplicate concurrent webhooks. Committed synthetic test fixtures are cleaned up in the guarded `_test` database.
- Fresh upgrade/downgrade and legacy payment preservation passed. Development migration applied; Alembic found no model/schema drift. Pip dependency check and React production build passed.
- No real Stripe credentials were configured and no Stripe account/sandbox transaction has been made yet. Real test-card confirmation, Stripe-delivered webhook, and rendered Payment Element remain **unverified**.
- Browser visual automation remains unavailable after the earlier URL-policy rejection. Do not substitute a build or mocked provider test for real browser/provider verification.

The progress log tracks the deferred real-provider/rendered-checkout tests and daily Git checkpoint. The user's 2026-10-18 exception allows Day 7 after the Day 6 code is reviewed, locally checked, committed, pushed, and verified against GitHub. Complete the deferred Stripe checks when the user returns to setup.

References: [PaymentIntents](https://docs.stripe.com/payments/payment-intents), [SDK resources and dictionaries](https://github.com/stripe/stripe-python#working-with-api-resources), [webhook signatures](https://docs.stripe.com/webhooks), [idempotent requests](https://docs.stripe.com/api/idempotent_requests), [test cards](https://docs.stripe.com/testing), and [Stripe sandboxes](https://docs.stripe.com/sandboxes).
