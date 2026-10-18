# Internship roadmap

Source: the mentor's nine-page **Cab Booking Platform - Python Stack** PDF, particularly the schedule on pages 4-5 and the React / optional Next.js stack on page 8.

This is the guide's sequence adapted to the user's choices: Python FastAPI, PostgreSQL, and React. Each day is a work milestone, not a promise that its scope takes one calendar day. Do not skip unfinished work merely to keep the two-week timeline.

The user subsequently chose custom FastAPI + PostgreSQL authentication instead of the guide's Clerk/Supabase Auth options. The database connection and user/session tables move into Day 1 to support it; the remaining Day 2 scope is unchanged.

## Daily plan

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

## Day 6 checklist (in progress)

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
- [ ] Finish the Day 6 review, commit, push, and verify its Git checkpoint.

On 2026-10-18, the user explicitly chose to defer Stripe setup and real-provider/rendered-checkout verification and continue to Day 7. Those items remain unchecked; provider test doubles and locally signed fixture events do not substitute for real sandbox verification. Commit, push, and verify the Day 6 code checkpoint before Day 7. This is an exception for the deferred checks, not a claim that the payment integration is fully verified.

## Choices to resolve at the relevant milestone

- Day 1 choices resolved: step-by-step teaching, confirmed GitHub repository, custom FastAPI/PostgreSQL authentication, and SQLAlchemy with local PostgreSQL.
- Day 2: extend the schema with PostGIS and Alembic migrations.
- Day 3 routing choice resolved: OSRM public demo for learning, with no API key. See `RIDE_BOOKING.md` for service limits and the production hosting decision still needed before deployment.
- Day 4 choice resolved: include the driver dashboard, availability, and nearby matching.
- Day 5 choice resolved: include realtime with FastAPI WebSockets and Redis.
- Day 6 onward: required service configuration for test payments, email, and deployment.

The PDF supplies project requirements and suggestions. The user's chosen stack and daily commit/push workflow govern our implementation. External credentials, accounts, and deployments are not assumed to exist merely because the PDF mentions them.
