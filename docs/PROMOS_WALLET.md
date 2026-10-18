# Day 10: promo codes and test-wallet top-ups

The goal is to reduce a completed ride's fare with a valid promo and record a rider's wallet credit only after a verified test-payment notification. FastAPI owns pricing and payment verification; PostgreSQL stores the discount, balance and credit ledger; React displays the saved result.

The user deferred Stripe account setup and real-provider/rendered-checkout verification. This milestone has automated verification with a controlled provider and signed event fixtures, not a verified Stripe sandbox transaction. Promo application and reading an empty wallet work without Stripe keys. Wallet spending, ride payment from wallet, transfers, withdrawals and refunds are outside this checkpoint.

## Step 1: update the database

From the backend terminal, using the existing local PostgreSQL and Redis services:

```bash
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/backend"
source .venv/bin/activate
export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"
python -m alembic upgrade head
python -m alembic current
```

The current revision is `0008_promos_wallet`. It adds:

| Record | Purpose |
| --- | --- |
| `promo_codes` | Percentage, discount cap, minimum fare, validity window and usage limits. |
| `promo_redemptions` | One immutable discount snapshot per ride: code, original fare, discount and final fare. |
| `users.wallet_balance` | Exact `NUMERIC(14, 2)` balance, initially zero for existing accounts. |
| `wallet_topups` | Durable owner, amount, retry key, provider reference and payment state. |
| `wallet_entries` | One positive credit per successful top-up. |
| `payment_events` | Existing global event-ID audit now targets exactly one ride payment or wallet top-up. |

The upgrade preserves existing ride payment/event records. Downgrading this revision deletes the new wallet/promo data and wallet-targeted event records while retaining ride payment events. Review backups before any downgrade; development was upgraded only. Migration round trips are tested transactionally in the separate test database.

## Step 2: create the learning promo

```bash
python -m scripts.seed_demo_promo
```

This local operator command creates `WELCOME10`: 10% off, capped at INR 50, minimum fare INR 80, at most 100 redemptions globally and one per rider. It is valid for 30 days from creation. Running the command again preserves the existing code, limits and expiry; it does not renew it. The command has already been run on this development database. No public code-management API is included.

Start the backend with the native PDF library path set as above:

```bash
python -m uvicorn app.main:app --reload --no-proxy-headers --ws-max-size 2048
```

In another terminal:

```bash
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/frontend"
npm run dev
```

Reuse an existing server on these ports. Open <http://127.0.0.1:5173/>.

## Step 3: apply a promo before checkout

1. Sign in as a rider and complete a trip using the [rider/driver walkthrough](LIVE_UPDATES.md).
2. Open its payment details, either on the current completed trip or through ride history.
3. Before opening checkout for the first time, enter `WELCOME10` and apply it. Lowercase codes are accepted; the API also trims surrounding whitespace.
4. Check the saved before/discount/final amounts. For a fare of INR 104.38, the discount is INR 10.44 and the final fare is INR 93.94.
5. Download the trip PDF from history. It includes the discount snapshot. An unpaid document remains a trip statement, not proof of payment.

Applying a promo requires an owned, completed ride with no invoice yet. Even a pending or failed existing invoice fixes the fare and prevents adding a promo. One code can be applied per ride; applying the same code again returns the same snapshot. Codes cannot be removed or stacked. Usage is consumed when applied, including if the invoice is not subsequently paid.

The server checks active status, start/expiry times, minimum fare, percentage, cap and global/personal limits. It rounds money with Decimal and retains a final fare of at least INR 50. That floor is our project's policy, not a universal Stripe minimum. The final fare is saved as `rides.fare_actual`; the original estimate is retained. Checkout later reads this saved fare. The browser cannot submit its own discount, final amount or rider ID.

The ride row lock serializes checkout against promo application. The promo row lock serializes usage counting so simultaneous requests cannot exceed its limit. A later code edit/expiry does not rewrite an existing redemption. PDF snapshots read the ride, invoice and redemption together, so a promo committed after a ride was initially loaded cannot mix an old total with a new discount. A newly requested receipt email uses the updated document fingerprint; an earlier saved email snapshot is preserved. See [history and receipts](HISTORY_RECEIPTS.md).

## Step 4: understand the test wallet

The rider page has a **Wallet balance** panel. Reading it needs no payment configuration. Existing accounts start at INR 0; there is no button that directly grants credits. It shows the latest five top-ups and ten verified credits, plus the complete saved balance. Driver accounts cannot use these APIs.

With Stripe setup deferred, top-up checkout remains disabled. When returning to setup, follow [the test-payment walkthrough](PAYMENTS.md). Wallet and ride payments share the configured test keys, signed `/api/webhooks/stripe` endpoint and PaymentIntent event types; no second webhook secret is required for the existing listener.

The later manual sandbox check is:

1. Configure the user's Stripe **test** keys and keep the local webhook listener running.
2. Open a test top-up for INR 100; supported amounts are INR 50–10,000 with at most two decimal places.
3. Use Stripe's test card `4242 4242 4242 4242`, a future expiry and test CVC in the test form. No real payment details are needed.
4. Confirm the browser waits for the signed notification. Verify one credit and a balance increase of INR 100 after the webhook, then refresh/reload and check it persists.
5. Check failure/retry behavior and repeat delivery of the same provider event without an extra credit. Check another rider cannot read or resume this top-up.

These steps are still unverified with the actual provider and rendered UI. Automated fixtures do not replace them.

**Retry this top-up** reuses its amount and request UUID after an uncertain response. **Continue test top-up** resumes a saved recent attempt after a reload. **Start another top-up** starts a new attempt; it does not cancel a previous provider intent. Review recent attempts before starting another. The current UI keeps its retry key in component memory; durable attempts are stored on the server, and older attempts can be read/resumed by their owned UUID through the API.

## How a credit becomes durable

1. FastAPI validates the authenticated rider, allowed Origin, amount and request UUID. It saves a top-up before provider I/O; the same user/key cannot create a second attempt or change its amount.
2. The top-up UUID supplies a stable Stripe idempotency key. A known intent is retrieved rather than recreated. Unlinked attempts older than 23 hours are refused and need operator reconciliation.
3. A browser confirmation or provider response alone cannot credit a wallet. The webhook verifies the raw-body signature and test event, then retrieves the canonical intent and checks its ID, amount, received amount, INR currency and project/kind/top-up/owner metadata.
4. PostgreSQL locks the top-up and owner. A successful verified payment inserts one uniquely linked ledger entry, increments the balance, marks the top-up credited and saves the globally unique event ID in one transaction.
5. Duplicate deliveries and distinct later events cannot credit the same top-up twice. Successful/cancelled records cannot regress. Different top-ups for one rider serialize balance updates to prevent lost credits.
6. After commit, an account-only `wallet.changed` notification prompts a fresh API read. The event contains no balance or payment details. Failed notifications leave committed data intact; **Refresh wallet** reads it again.

Provider timeouts, missing deliveries and old unlinked attempts require reconciliation; no scheduled reconciliation worker is included. Refund/reversal accounting and production wallet operation require further design before real-money use. Local tests do not establish production readiness.

## APIs and files

All routes require the existing session except the signed webhook; writes additionally require the allowed browser Origin. Ownership failures return 404 and role failures are rejected. Protected responses use the existing no-store policy. Wallet responses do not expose provider IDs or client secrets; checkout secrets are returned only for the owned checkout and kept in component memory.

| Method and path | Purpose |
| --- | --- |
| `GET /api/rides/{ride_id}/promo` | Read the completed ride's own applied snapshot or null. |
| `POST /api/rides/{ride_id}/promo` | Apply `{"code":"WELCOME10"}` before invoice creation. |
| `GET /api/wallet` | Own balance, latest credits and recent attempts. |
| `GET /api/wallet/topups/{topup_id}` | Own attempt's saved status. |
| `POST /api/wallet/topups` | Create/retry with `amount` and UUID `request_key`. |
| `POST /api/wallet/topups/{topup_id}/payment-intent` | Resume an owned attempt with `{}`. |
| `POST /api/webhooks/stripe` | Shared raw-body signed ride/top-up notification. |

| File | What to learn |
| --- | --- |
| `backend/app/promos.py` | Eligibility, Decimal pricing, row locks and a frozen discount. |
| `backend/app/wallet.py` | Durable retries, canonical verification and atomic credits. |
| `backend/app/wallet_schemas.py` | Strict input validation and safe public responses. |
| `backend/app/stripe_validation.py` | Shared test-intent validation for both kinds of payments. |
| `backend/alembic/versions/0008_promos_wallet.py` | Versioned schema and data-preserving upgrade. |
| `backend/scripts/seed_demo_promo.py` | Explicit local promo creation. |
| `frontend/src/Wallet.jsx` | Saved status, amount validation, retry/resume and live refresh. |
| `frontend/src/RidePayment.jsx` | Promo form and reusable test-card form. |

## Verification at this checkpoint

The complete backend suite passed **230 tests** with the existing TestClient/HTTPX deprecation warning. React's production build, pip consistency and Alembic no-drift checks passed. The development migration is applied; the promo seed's repeat run preserved it. The updated synthetic promo PDF was rendered and visually inspected as one readable page.

Tests cover promo eligibility, rounding/caps, invoice exclusion, ownership, strict inputs, migration preservation, signature validation, canonical amount/metadata/mode mismatches, retry keys, cross-kind event audit IDs, duplicate credits, status ordering and private Redis/WebSocket notification projection. Eight separate-connection concurrency scenarios cover promo retries/limits/invoice races and wallet creation/same-event/different-event/different-top-up credit races. A further two-session receipt regression reproduced an old-total/new-discount mismatch before the snapshot fix and passes afterward. Provider calls use a controlled double; signature parsing uses the Stripe SDK. Wallet tests do not charge or contact Stripe.

To rerun, from `backend/` with the PDF library path set and local PostgreSQL/Redis running:

```bash
python -m pytest -q
python -m pip check
python -m alembic check
```

Tests require the separate `_test` database, use Alembic and isolate/clean up their test resources. From `frontend/`, `npm run build` bundles the React application. Build success is not a browser interaction pass; earlier browser automation remains unavailable and manual UI checks are pending.

Provider references: [PaymentIntent creation and idempotency](https://docs.stripe.com/api/payment_intents/create), [signed webhooks](https://docs.stripe.com/webhooks), and [currency/minimum-charge rules](https://docs.stripe.com/currencies). Existing [PAYMENTS.md](PAYMENTS.md) explains local test setup and outstanding provider checks.
