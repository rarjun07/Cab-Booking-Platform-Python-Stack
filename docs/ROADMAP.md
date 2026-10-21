# Internship roadmap

Source: the mentor's nine-page **Cab Booking Platform - Python Stack** PDF, particularly the schedule on pages 4-5 and the React / optional Next.js stack on page 8.

This is the guide's sequence adapted to the user's choices: Python FastAPI, PostgreSQL, and React. Each day is a work milestone, not a promise that its scope takes one calendar day. Do not skip unfinished work merely to keep the two-week timeline.

The user subsequently chose custom FastAPI + PostgreSQL authentication instead of the guide's Clerk/Supabase Auth options. The database connection and user/session tables move into Day 1 to support it; the remaining Day 2 scope is unchanged.

## Daily plan

The user requested completion of audited gaps on 2026-10-21. Follow the sequential [feature follow-ups](FEATURE_COMPLETION.md), retaining individual Git checkpoints and all existing Day 14/provider/manual verification limits.

| Day | Scope from the guide | Evidence before the daily Git checkpoint |
| --- | --- | --- |
| 1 | Initialize `backend/` and `frontend/`; FastAPI scaffold; custom PostgreSQL-backed authentication and signed session verification (user's adaptation). | Both apps run; real registration/login/logout work; FastAPI rejects invalid, missing, expired, and revoked sessions. |
| 2 | Extend the PostgreSQL setup with PostGIS, remaining SQLAlchemy models, and Alembic migrations. | Migrations include the existing auth schema and add driver, ride, payment, and review models; the geospatial setup is verified. |
| 3 | Fare estimation and ride request creation; OSRM replaces Google Maps at the user's request for a free alternative. | A real road-route estimate can be requested and a ride request persists in PostgreSQL. |
| 4 | Optional driver dashboard, nearby-driver queries, matching, and availability. | If included, availability and nearby-driver matching work with sample data. If deferred, record the decision before proceeding. |
| 5 | Optional realtime rider/driver connections and location updates with WebSockets or Socket.IO plus Redis. | If included, an authenticated rider receives the relevant driver's updates. If deferred, record the decision before proceeding. |
| 6 | Stripe PaymentIntents and signed payment webhooks. | Stripe test-mode payment flow works and verified webhook events update payment state. |
| 7 | Buffer, endpoint tests, and manual flow checks. | Tests pass and issues found in the first week's implemented flows are resolved or explicitly tracked. |
| 8 | Ride history, PDF receipts, and Celery receipt-email tasks. | A completed ride appears in history, has a readable receipt, and can trigger the configured background email task. |
| 9 | Ratings and reviews with aggregation. | Authorized participants can submit valid reviews and rating summaries update correctly. |
| 10 | Promo codes and wallet top-ups using Stripe. | Promo rules and balances work; a verified test payment credits the wallet once. |
| 11 | React UI polish, accessibility, and mobile responsiveness. | Implemented screens work on desktop and mobile and support keyboard interaction. |
| 12 | Redis rate limits, CORS, validation, database indexes, and query performance. | Relevant security and performance checks pass for the implemented features. |
| 13 | End-to-end tests and multiple-driver / multiple-ride scenarios. | Core end-to-end flows pass; test coverage reflects any optional features actually included. |
| 14 | Dockerfiles, local Compose services, and deployment. | Container startup is verified and the configured deployed application passes smoke checks. |

Days 4 and 5 are explicitly optional in the guide. The guide also labels geospatial queries optional in its notes, while its Day 2 schedule includes PostGIS setup. Keep PostGIS in the planned database setup; decide the optional matching features when reaching Day 4.

The user chose to include both Day 4 and Day 5.

## Day 1 checklist

- [x] Confirm the project repository URL and local GitHub access.
- [x] Set up Git and a `.gitignore`.
- [x] Add safe environment-variable examples when authentication configuration is introduced.
- [x] Create the `backend/` FastAPI application and development environment.
- [x] Create the `frontend/` React application.
- [x] Confirm custom FastAPI + PostgreSQL authentication (user's explicit choice replacing the guide's provider options).
- [x] Configure dedicated development/test databases and ignored local secrets.
- [x] Implement frontend registration, sign-in, and sign-out.
- [x] Verify signed tokens and PostgreSQL sessions in FastAPI and add a protected session endpoint.
- [x] Check frontend-to-backend connectivity and authentication success and failure paths.
- [x] Document local startup steps and explain the files added.
- [x] Record verification results in `PROGRESS.md`.
- [x] Commit Day 1 with a descriptive commit message.
- [x] Push Day 1 to the confirmed repository and verify the remote application commit (`dcf9340`).

Do not begin the remaining Day 2 database models or migrations until every required Day 1 item, including the push, is complete. Authentication must work with real PostgreSQL persistence; placeholder screens or mocked tokens do not satisfy it.

## Day 2 checklist

- [x] Confirm the Day 1 commit/push checkpoint before starting.
- [x] Install and enable PostGIS for the existing project PostgreSQL server.
- [x] Extend user fields and add driver, ride, payment, and review models.
- [x] Add foreign keys, uniqueness/check constraints, exact money types, and spatial indexes.
- [x] Introduce Alembic with checked adoption of the existing auth schema.
- [x] Apply migrations without changing existing account/session records.
- [x] Verify spatial operations, model constraints, fresh upgrades, downgrade behavior, and auth regressions.
- [x] Document schema inspection and migration commands.
- [x] Commit Day 2 and push it to GitHub (`4ae8200`).
- [x] Verify the remote implementation commit before Day 3.

## Day 3 checklist

- [x] Verify the Day 2 Git checkpoint before starting (`af94813`).
- [x] Resolve the routing provider: the user chose a free alternative; use OSRM/OpenStreetMap.
- [x] Add authenticated road-route estimates with validation, timeouts, caching, and throttling.
- [x] Calculate illustrative INR fares on the server and issue expiring, rider-bound signed quotes.
- [x] Persist ride requests with PostGIS points and duplicate protection through Alembic migration `0003_ride_quote`.
- [x] Add owned ride status access and a React booking form.
- [x] Pass backend tests and the frontend build; verify the real OSRM and ride API flow.
- [x] Document setup, limitations, and verification evidence.
- [x] Commit, push, and verify the Day 3 implementation (`ef48c41`).
- [ ] Manual/visual UI follow-up: browser policy blocked automated preview; user has not tried the form yet. Track this separately from the verified API flow.

## Day 4 checklist

- [x] Verify the Day 3 completion-record commit on GitHub (`8d59f1c`).
- [x] Resolve optional scope: user chose to include Day 4.
- [x] Add driver-owned vehicle setup and online/offline location updates.
- [x] Add location freshness, indexed meter-based radius queries, and sorted nearby offers/candidates.
- [x] Add accept/decline matching with authorization and eligibility rechecks.
- [x] Prevent competing assignments with row locks and a unique active-driver index.
- [x] Add the React driver dashboard, rider candidate list, and current-ride recovery.
- [x] Apply the migration and verify preservation, backend tests, frontend build, and the live API demo.
- [x] Document the two-account walkthrough and demo/verification limits.
- [x] Commit, push, and verify the Day 4 implementation (`834ae6e`).
- [ ] Manual/visual UI follow-up: preview automation remains blocked by the earlier URL-policy rejection. User feedback is recorded separately in `PROGRESS.md`.

## Day 5 checklist

- [x] Verify the Day 4 completion-record commit on GitHub (`1af381c`).
- [x] Resolve optional scope: user chose to include Day 5.
- [x] Add WebSockets using the existing cookie and strict Origin/role/account checks.
- [x] Recheck session expiry/revocation on connected sockets and clean up subscriptions/tasks.
- [x] Use namespaced Redis Pub/Sub to bridge backend processes with no private fields on shared channels.
- [x] Publish after database commits and preserve HTTP success if notifications fail.
- [x] Add assigned-rider location access, validated driver sharing, and authorized trip progression.
- [x] Add React connection status, coalesced refreshes, reconnect recovery, and manual fallbacks.
- [x] Verify real WebSocket/Redis tests, backend regressions, schema/dependencies, frontend build, Vite upgrades, and cross-process delivery.
- [x] Document setup, two-window demo, security, and limitations.
- [x] Commit, push, and verify the Day 5 implementation (`4a99f39`).
- [ ] Manual/visual UI follow-up: earlier browser policy blocks automated preview; user has not tried the connection-badge check yet.

## Day 6 checklist (code pushed; Stripe verification deferred)

- [x] Verify Day 5's final documentation commit on GitHub (`0d465f9`).
- [x] Add a versioned payment currency/timestamp and webhook audit schema while preserving existing rows.
- [x] Create owner-only checkout for completed rides using a frozen stored fare and stable idempotency key.
- [x] Verify raw-body signatures, canonical Stripe state/amount/metadata, duplicate events, and out-of-order events.
- [x] Add test-only key validation, disabled checkout without configuration, and a hidden-prompt local setup helper.
- [x] Add React Payment Element checkout, payment status refresh, and completed-ride restoration.
- [x] Pass backend tests, schema/dependency checks, and the React production build.
- [x] Verify local HTTP behavior with keys absent; unsigned webhooks are rejected and checkout is disabled.
- [ ] Configure the user's Stripe sandbox/test keys and local webhook listener.
- [ ] Complete a real Stripe test transaction and verify a Stripe-delivered signed webhook updates the matching invoice.
- [ ] Verify rendered checkout success/failure/retry behavior; prior browser automation remains unavailable.
- [x] Finish the Day 6 code review, local checks, commit, push, and verify its Git checkpoint (`d2e9e77`).

On 2026-10-18, the user explicitly chose to defer Stripe setup and real-provider/rendered-checkout verification and continue to Day 7. Those items remain unchecked; provider test doubles and locally signed fixture events do not substitute for real sandbox verification. Commit, push, and verify the Day 6 code checkpoint before Day 7. This is an exception for the deferred checks, not a claim that the payment integration is fully verified.

## Day 7 checklist (tests pushed; follow-ups tracked)

- [x] Verify the Day 6 code commit on GitHub (`d2e9e77`) before beginning, with the user's Stripe deferral recorded.
- [x] Add a connected API journey covering accounts, signed quotes, duplicate booking, matching, guarded progression, restoration, disabled payments, and revoked-session replay.
- [x] Run the complete backend regression suite and review first-week issues: 145 tests passed; no new application fix was required.
- [x] Document beginner-friendly test commands and a manual two-account checklist in `TESTING.md`.
- [x] Explicitly track pending browser checks, user-deferred Stripe verification, and the existing TestClient warning.
- [x] Review, commit, push, and verify the Day 7 implementation checkpoint (`4746d17`); final documentation checkpoint `f415d80` was verified before Day 8.

## Day 8 checklist (implementation pushed; manual follow-up tracked)

- [x] Verify Day 7's final documentation checkpoint on GitHub (`f415d80`) with a clean working tree.
- [x] Add participant-owned completed/cancelled history with stable bounded cursor pagination.
- [x] Generate private completed-trip PDFs with WeasyPrint, escaped text and no external resource fetches; distinguish unpaid statements from test-payment receipts.
- [x] Add durable versioned email requests through Alembic, Celery/Redis publication, bounded worker retries and explicit status access.
- [x] Add React history, PDF download, email controls, and older rider payment details.
- [x] Verify real Celery/Redis/local SMTP delivery with a PDF attachment and duplicate-task handling; no external email sent.
- [x] Pass 157 backend tests, React build, pip consistency and schema checks; render/visually inspect the PDF sample.
- [x] Document native PDF dependencies, four-terminal local setup, retry/delivery limits and manual UI follow-ups.
- [x] Review, commit, push, and verify the Day 8 implementation checkpoint (`f70387c`) before Day 9.
- [ ] Manual/visual React follow-up: page history, download/open a PDF, use the local catcher and check account separation; prior browser automation rejection remains unresolved.

## Day 9 checklist (implementation pushed; manual follow-up tracked)

- [x] Verify Day 8's final documentation checkpoint on GitHub (`9f59017`) with a clean working tree.
- [x] Add completed-trip participant review reads/writes with server-selected recipients, strict 1-5 ratings and bounded plain-text comments.
- [x] Reuse one-review-per-author/trip uniqueness; return identical retries without duplicating feedback and reject conflicting submissions.
- [x] Commit reviews and cached averages together, and compute summary average/count consistently; verify five concurrent-write scenarios.
- [x] Apply `0007_review_timestamps`, preserve legacy feedback/unknown dates, and reconcile derived rating averages.
- [x] Add history review forms, saved/received feedback and own summaries; keep mounted forms during background live refresh.
- [x] Verify participant-only Redis/WebSocket notifications with no private comment payload or matching broadcast.
- [x] Finish final backend regressions/source review: 184 tests, React build, schema/dependency checks and source checks passed.
- [x] Document the two-account walkthrough, eligibility, aggregation and known manual follow-ups in `REVIEWS.md`.
- [x] Commit, push and verify the Day 9 implementation checkpoint (`90bc586`) before Day 10.
- [ ] Manual browser follow-up: submit/read both participants' feedback, check averages/reload, and confirm drafts survive live sync. Earlier browser automation remains blocked.

## Day 10 checklist (implementation pushed; deferred checks tracked)

- [x] Verify Day 9's final documentation checkpoint on GitHub (`2bd51f9`) with a clean working tree.
- [x] Add completed-trip promos before invoice creation, eligibility/limit checks, frozen Decimal discounts and invoice/PDF integration.
- [x] Add Alembic `0008_promos_wallet`, preserve ride payment events and initialize existing balances to zero.
- [x] Add durable top-up retry keys, owned resume/status and signed canonical test-payment validation.
- [x] Atomically credit a uniquely linked ledger/balance once; verify concurrent requests/events/top-ups and promo/invoice races.
- [x] Add React promo/wallet panels, reusable test-card form and private live refresh with manual fallbacks.
- [x] Pass 230 backend tests, React build, schema/dependency checks and visual inspection of the discounted sample PDF; reproduce/fix a concurrent promo/receipt stale-total race.
- [x] Document local `WELCOME10` setup, workflow, retry/reconciliation limits and deferred checks in `PROMOS_WALLET.md`.
- [x] Review, commit, push and verify the Day 10 implementation (`561181c`) before Day 11.
- [ ] Deferred with the user's earlier Stripe setup decision: verify a real Stripe sandbox top-up and signed provider delivery credit exactly once.
- [ ] Manual browser follow-up: apply a promo, inspect the PDF, check wallet balance/retry/resume/reload and rendered payment success/failure.

Controlled provider tests and locally signed fixtures verify application logic; they do not satisfy the outstanding real-provider check. Wallet spending/refunds are outside Day 10's top-up scope. Day 11 has not started.

## Day 11 checklist (code checkpoint verified; manual checks pending)

- [x] Verify Day 10's final documentation checkpoint on GitHub (`5c93b72`) with a clean working tree.
- [x] Polish role-aware navigation/copy, card spacing, controls, rider workspace layout and narrow-screen stacking/wrapping.
- [x] Improve skip/section targets, explicit account-action focus, repeated payment IDs, history disclosure semantics and field hints.
- [x] Add targeted component checks for guest/rider/driver structure and keyboard/account/promo/review behavior; 9 tests passed.
- [x] Pass the React production build; preserve production dependency pins and backend/API/schema behavior.
- [x] Document the implementation, test boundaries and desktop/mobile/zoom/keyboard/screen-reader checklist in `UI_POLISH.md`.
- [x] Review, commit, push and verify the Day 11 code checkpoint (`a8bf1f8`).
- [ ] Actual browser/mobile/zoom/keyboard/screen-reader follow-up remains unverified. The user repeatedly requested continuation after the reminder; carry this pending item into later work without claiming a browser pass.

Day 11's code checkpoint is verified. The user requested continuation; Day 12 proceeds with earlier manual UI and deferred Stripe checks still pending.

## Day 12 checklist (implementation checkpoint verified)

- [x] Verify Day 11's final documentation checkpoint on GitHub (`caf8c1a`) with a clean working tree; retain the pending manual-review status.
- [x] Add atomic shared Redis quotas for API/auth/estimate/checkout/document requests and WebSocket handshakes; handle exhaustion and Redis failure explicitly.
- [x] Add bounded request-body reads, safe response headers and strict credentialed CORS while preserving Origin/session/ownership checks and signed Stripe bytes.
- [x] Tighten unknown-field, finite-coordinate and PostgreSQL-safe text validation; bound incoming WebSocket message frequency.
- [x] Apply index-only migration `0009_query_indexes` with row preservation; improve history/wallet/promo access paths and remove per-offer coordinate queries.
- [x] Verify actual query plans on synthetic test data, Redis concurrency/TTL/failure and API/WebSocket boundary behavior.
- [x] Pass 263 backend tests, 9 React component checks, production build and schema/dependency checks.
- [x] Document limits, startup/proxy settings, test isolation, plan evidence and outstanding service/UI checks in `SECURITY_PERFORMANCE.md`.
- [x] Review, commit, push and verify the Day 12 code checkpoint (`713017c`) before Day 13.

Day 12's code checkpoint is verified. Pending manual UI and actual Stripe verification remain tracked.

## Day 13 checklist (implementation checkpoint verified)

- [x] Verify Day 12's final documentation checkpoint (`75b0a6f`) against GitHub before implementation; retain pending UI/Stripe status.
- [x] Add a real local HTTP/WebSocket multi-account journey with actual migrated PostgreSQL, Redis quotas/notifications and separate client cookies.
- [x] Cover request retries, assignment/release, progression, private history, promo/invoice retries, signed fixture events, reviews and wallet credits.
- [x] Deliver the discounted test-payment PDF through real local Celery/Redis/SMTP and verify receipt status, ownership and session revocation.
- [x] Exercise actual HTTP competing-driver/competing-ride requests and stale, distant and declined-driver eligibility.
- [x] Reproduce and fix the actual GET-estimate quota gap; add React booking-recovery/quota/session tests.
- [x] Pass 268 backend tests, 11 React tests, production build and schema/dependency checks; verify owned test data/Redis keys were removed.
- [x] Document API/service versus simulated/browser/provider boundaries in `END_TO_END_TESTING.md`.
- [x] Review, commit, push and verify Day 13 (`97a992e`) before Day 14.

Day 13's checkpoint is verified. Manual browser/UI and actual Stripe-provider checks remain pending.

## Day 14 checklist (prepared; runtime verification pending)

- [x] Verify Day 13's documentation checkpoint (`e91e92e`) against GitHub before implementation.
- [x] Prepare backend/frontend Dockerfiles, build-context allowlists and an Apple Silicon-compatible PostgreSQL/PostGIS image.
- [x] Prepare private Compose database/Redis, one-shot migrations, non-root API/worker, nginx HTTP/WebSocket proxy and independent ignored configuration.
- [x] Add configuration-safety tests and a real-container smoke script with account cleanup and restart checks.
- [x] Pass configuration-safety tests, static Compose validation and native React production build.
- [ ] Resolve Docker's internal read-only storage error; rebuild all images successfully.
- [ ] Verify startup, SQL role/migrations/PostGIS, authentication, forwarded-header quota, WebSockets, Linux PDF, worker task and restart persistence in containers.
- [x] Review, commit, push and verify the prepared Day 14 checkpoint (`8b2c2c2`), explicitly retaining unfinished storage/runtime/deployment checks.
- [ ] Choose/configure online hosting, HTTPS, routing/storage/provider settings and verify the actual deployed URL.

No container runtime or online deployment pass is claimed. See `DEPLOYMENT.md` and `PROGRESS.md` for commands and the storage error evidence. Earlier manual UI and actual Stripe-provider checks remain pending.

## Choices to resolve at the relevant milestone

- Day 1 choices resolved: step-by-step teaching, confirmed GitHub repository, custom FastAPI/PostgreSQL authentication, and SQLAlchemy with local PostgreSQL.
- Day 2: extend the schema with PostGIS and Alembic migrations.
- Day 3 routing choice resolved: OSRM public demo for learning, with no API key. See `RIDE_BOOKING.md` for service limits and the production hosting decision still needed before deployment.
- Day 4 choice resolved: include the driver dashboard, availability, and nearby matching.
- Day 5 choice resolved: include realtime with FastAPI WebSockets and Redis.
- Day 6 onward: required service configuration for test payments, email, and deployment.

The PDF supplies project requirements and suggestions. The user's chosen stack and daily commit/push workflow govern our implementation. External credentials, accounts, and deployments are not assumed to exist merely because the PDF mentions them.
