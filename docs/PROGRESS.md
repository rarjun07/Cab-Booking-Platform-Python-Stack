# Project progress

## Current checkpoint

- Active milestone: Day 14 container/deployment setup in progress. Dockerfiles, isolated Compose services, a credential helper and smoke script are prepared. The build hit a Docker internal read-only filesystem error; container startup/smoke checks have not passed. Recovery may interrupt another project's running database and awaits the user's response. Browser/mobile/zoom/screen-reader checks remain pending; earlier Stripe setup/real-provider/rendered-checkout deferral remains in effect.
- Completed: read all nine PDF pages, checked the daily schedule, confirmed stack compatibility, and prepared the roadmap.
- Learning preference: guide the user step by step with explanations.
- Day 1 implementation: complete; custom FastAPI + PostgreSQL authentication is verified with real database tests and browser flows.
- Git repository: local `main` tracks `origin/main`.
- GitHub account supplied by user: `rarjun07`.
- GitHub access: verified with `gh auth status`; `rarjun07` is the active account.
- Repository URL: https://github.com/rarjun07/Cab-Booking-Platform-Python-Stack (supplied by user).
- Remote: `origin` -> `https://github.com/rarjun07/Cab-Booking-Platform-Python-Stack.git` (fetch and push verified locally).
- Repository verification: `gh repo view` confirmed the intended owner/name and that the repository was empty before our first push.
- Day 1 application commit: `dcf934062abca7bab47464104d13ca2b7a94bb45` (`feat: complete day 1 setup and PostgreSQL authentication`).
- Verified application push: `git ls-remote origin refs/heads/main` returned that exact SHA after the first push.
- This completion record is saved in a following documentation commit. For the latest checkpoint commit, compare `git rev-parse HEAD` with `git ls-remote origin refs/heads/main`.
- Day 2 implementation commit: `4ae8200b1345a202c18a4ab4ea2296f3e9a82030` (`feat: complete day 2 PostGIS models and Alembic migrations`).
- Verified Day 2 push: GitHub `refs/heads/main` matched that exact SHA. This completion record follows in a documentation commit; compare current HEAD and the remote for the latest checkpoint.
- Day 2 documentation checkpoint: `af94813132f8a08456d8ed90062d29cd730fe701`, verified against GitHub before Day 3 started.
- Day 3 implementation commit: `ef48c41770db6eedb4392f350176f9fb379049ec`, pushed and verified against GitHub `refs/heads/main`.
- Day 3 documentation checkpoint: `8d59f1c5b04fcf3687beba196e58d2b6c57f29aa`, confirmed equal to GitHub before Day 4 started; working tree was clean.
- Day 4 implementation commit: `834ae6e413fadb6a5e1c61a2c66d0d19191fe5b9`, pushed and verified against GitHub `refs/heads/main`.
- Day 4 documentation checkpoint: `1af381c19bcabe7bc2c46e5d93803022e5dbd3e1`, verified against GitHub before starting Day 5; working tree was clean.
- Day 5 implementation commit: `4a99f39759ec485565597b570a02b6866006530d`, pushed and verified against GitHub `refs/heads/main`.
- Day 5 documentation checkpoint: `0d465f99e1c8585741f9d610add7dd63f3258422`, verified against GitHub before Day 6; working tree was clean.
- Day 6 code checkpoint: `d2e9e778969be525ee5ff1a7983b1e185ffbf63d`, pushed to `origin/main`; `git ls-remote` returned that exact SHA. Working tree was clean before Day 7 began.
- Day 7 implementation checkpoint: `4746d1750d948db614feca1619a552a3e22a41fc`, pushed to `origin/main`; `git ls-remote` returned that exact SHA. This completion record follows in a documentation commit; compare current HEAD with GitHub for the latest checkpoint.
- Day 7 documentation checkpoint: `f415d80e2dbeacfcd8c4666818a5e818e3276ea9`, verified equal to GitHub before Day 8; the working tree was clean.
- Day 8 implementation checkpoint: `f70387c95fbf4e69736a3a7ee6b41f6c875da426`, pushed to `origin/main`; `git ls-remote` returned that exact SHA. This completion record follows in a documentation commit; compare current HEAD with GitHub for the latest checkpoint.
- Day 8 documentation checkpoint: `9f59017d2d4d39453aefb2a1fcd6f0c0e3a61e2f`, verified equal to GitHub before Day 9; working tree was clean.
- Day 9 implementation checkpoint: `90bc586f9690772e0cac78654cb73a5d73305a76`, pushed to `origin/main`; `git ls-remote` returned that exact SHA. This completion record follows in a documentation commit; compare current HEAD and GitHub for the latest checkpoint.
- Day 9 documentation checkpoint: `2bd51f92f28fc3dc40877991207d9ca22ba1dc9c`, verified equal to GitHub before Day 10; working tree was clean.
- Day 10 implementation checkpoint: `561181c9b33fadc1f68df01609abee66b3d56ca8`, pushed to `origin/main`; `git ls-remote` returned that exact SHA. This completion record follows in a documentation commit; compare current HEAD and GitHub for the latest checkpoint.
- Day 10 documentation checkpoint: `5c93b7278c90ebb86568a7d58d176b8334152beb`, verified equal to GitHub before Day 11; working tree was clean.
- Day 11 implementation checkpoint: `a8bf1f87adf641d58e422e0683070843622a16cb`, pushed to `origin/main`; `git ls-remote` returned that exact SHA. This completion record follows in a documentation commit; compare current HEAD and GitHub for the latest checkpoint.
- Day 11 documentation checkpoint: `caf8c1af22dec626aade98455052b5237d6327cf`, verified equal to GitHub before Day 12; working tree was clean.
- Day 12 implementation checkpoint: `713017c28dc3812adcecabd765cddd381e23cf35`, pushed to `origin/main`; `git ls-remote` returned that exact SHA. This completion record follows in a documentation commit; compare current HEAD and GitHub for the latest checkpoint.
- Day 12 documentation checkpoint: `75b0a6fbb9fd628c82f33273c58af70f79529940`, verified equal to GitHub before Day 13; working tree was clean at that boundary. Remote remained at this checkpoint when work resumed on 2026-10-20.
- Day 13 implementation checkpoint: `97a992e7f4385b8e65f0de4889e7bd226ec09374`, pushed to `origin/main`; `git ls-remote` returned that exact SHA. This completion record follows in a documentation commit; compare current HEAD and GitHub for the latest checkpoint.
- Day 13 documentation checkpoint: `e91e92e6634004b058a07f537d283e881862e2cb`, verified equal to GitHub before Day 14 with a clean working tree.
- Day 14 prepared-code checkpoint: `8b2c2c2665889ec063a086a6e5c6f640b16d166b`, committed/pushed and verified equal to GitHub `refs/heads/main`. This saves incomplete Day 14 work; it does not certify container startup or deployment. This verification record follows in a documentation commit.
- Next action: resolve Docker storage/recovery, rebuild and run Compose and the restart smoke check; choose a hosting destination before any online deployment. Day 14 is incomplete. Manual UI/actual Stripe verification remain pending.

## User-requested dashboard layout — 2026-10-21

- The user requested better aligned rider and driver dashboards comparable to a finished website, carrying forward the existing UI-color constraint. The working tree was clean at the verified header checkpoint `2a3c7fe` before these edits. This is a requested UI follow-up; Day 14 container/deployment verification remains incomplete.
- Replaced the long stacked signed-in page with a shared sidebar, compact heading/live status and focused booking/driver, wallet (riders), history and account views. Added `WorkspaceNavigation.jsx` with account identity, role-specific links and an active-page indicator. Fragment bookmarks, modified-click links and browser navigation are preserved; invalid role views fall back to the primary workspace.
- Kept the account panel and inactive workspace views mounted so account restoration, form drafts, live data and payment/review controls survive view changes. Explicit hidden styling removes inactive content from layout and the keyboard sequence. Successful registration/login opens the proper role workspace and focuses its visible heading; account/header/sidebar navigation retains explicit focus behavior.
- Reorganized rider pickup/destination fields beside real estimate/current-ride content, and driver vehicle/availability cards beside request/current-trip content. The guest introduction and account form share a desktop row. Shared spacing/container widths align header, sidebar, cards and footer; responsive breakpoints stack the columns and adapt navigation. No fabricated maps, earnings or statistics were added.
- All **21 frontend tests passed**, including structural accessibility audits of guest/rider/driver and each role's account/history/wallet views, navigation/deep-link behavior, rider route/driver vehicle draft retention, role-specific sign-in/focus and existing booking retry/quota cases. Production build passed (31 modules, 294.87 kB JS / 89.33 kB gzip); palette comparison confirmed only existing colors; `git diff --check` passed. Backend/schema/API contracts, dependency pins and private configuration are unchanged.
- No browser/mobile/zoom/screen-reader visual pass is claimed. Earlier browser automation restriction remains in effect; `UI_POLISH.md` contains the updated manual review checklist. No deployment or subsequent day was started.

## User-requested header update — 2026-10-21

- The user supplied current-page screenshots and a reference header, requesting top Login/Register/profile controls while retaining the current UI and colors. This is an explicitly requested UI follow-up; it does not advance or complete Day 14.
- Added a named account navigation in the existing header. Guest Login/Register buttons select the existing account form, focus its first field and bring it into view; repeated clicks work. The profile icon opens the current account section. Restored/signed-in accounts show the profile shortcut instead of guest actions; signing out restores those actions.
- Reused the existing cream, dark-green, lime and border colors, brand, project label, focus ring and typography. Responsive header wrapping affects only the header; existing page sections/styles remain intact. Authentication endpoints, cookie handling, backend/schema and dependencies are unchanged.
- Verification: all **13 frontend tests passed**, including new form-selection/focus, restored-account and logout navigation checks; existing guest/rider/driver structural accessibility and keyboard tests still pass. The production build and `git diff --check` passed. No rendered-browser/mobile/visual pass is claimed; earlier browser automation restriction and manual UI follow-ups remain pending.

## Day 14: container setup prepared; Docker storage recovery pending

- Started on the user's “next” instruction after verifying the clean Day 13 documentation checkpoint `e91e92e` against GitHub.
- Prepared a Python 3.14 backend image with pinned packages, Linux Pango/fonts, a non-root user and no development secrets/build context. Prepared a multi-stage Node 24/nginx React image with HTTP/WebSocket proxying, overwritten forwarded headers and a single explicitly trusted proxy address.
- Added a PostgreSQL 17/PostGIS build based on the official multi-architecture PostgreSQL image rather than the currently amd64-only upstream PostGIS image. New-volume administrator initialization creates a separate database, PostGIS extension and a restricted application login. Native PostgreSQL and existing development data were not changed.
- Added private Compose data services, persistent database/Redis AOF volumes, health/dependency conditions, a one-shot Alembic service, API/worker scratch space and a loopback-only web port 8080. No app/data host port or external deployment was configured.
- Generated independent Docker configuration in ignored `.env.database`/`.env.compose`, both mode `0600`, without changing `backend/.env`. The helper refuses overwrite and symlinks. Three new safety regression tests passed with `python3 -m unittest discover -s tests -v`.
- Static verification passed: Compose quiet validation; parsed Compose checks for private ports, secret separation, internal data network and migration ordering; Python syntax; shell syntax; source-secret scan across 19 candidate files; `git diff --check`. Native React production build passed (30 modules, 288.91 kB JS / 87.60 kB gzip). Existing application/API/schema code and dependency pins are unchanged; the prior 268 backend/11 frontend test result belongs to Day 13 and is not reported as a new Day 14 run.
- Added `scripts/smoke_compose.py` for real proxy/auth/Origin/quota/WebSocket, SQL role/PostGIS, Linux PDF, Celery consumption and optional restart-persistence checks. **This script has not run against containers yet.** It cleans only its generated account/session data and makes no routing/Stripe/external email calls.
- Docker Desktop 4.95.0/Engine 29.8.2 and Compose 5.6.0 are installed and reachable with required socket permission. The build successfully exported the dedicated database image and installed the pinned Python packages, then failed saving the backend layer: `write /var/lib/docker/buildkit/containerd-overlayfs/metadata_v2.db: read-only file system`. A complete image build and container startup are therefore unverified.
- Read-only diagnosis: the Mac data volume had approximately **3.2 GiB free (99% used)**. Docker reported 1.652 GB images, 1.419 GB build cache and one existing non-project container (`piston-prime-local-db16`, published on loopback 5433). Low free space is observed; the exact cause of Docker's read-only transition is not proven. No pruning, reset, file deletion or Docker restart was performed. The user was asked about freeing space/restart because restarting Desktop would interrupt that other database.
- Asked about hosting destination while preparing local files; no server/domain was supplied. Online deployment and deployed-URL smoke checks remain pending. `docs/DEPLOYMENT.md` explains the files/commands, backups, local limitations, Docker recovery and target-specific HTTPS/provider follow-ups. Day 14 is **not complete**.
- Reviewed and saved prepared implementation as `8b2c2c2`; push succeeded and GitHub returned exact SHA `8b2c2c2665889ec063a086a6e5c6f640b16d166b`. No later day or additional milestone was started. Docker recovery/runtime verification is the next required work.

## Day 1, step 1: local Git setup

- Initialized Git with `git init -b main`.
- Added `.gitignore` for local environment files, Python environments/caches, React dependencies/build output, and local editor/log files.
- Checked Git, Python, Node.js, npm, and local Git author configuration.
- Available tools: Git 2.50.1, Python 3.14.2, Node.js 24.18.0, npm 11.16.0.
- Confirmed GitHub authentication for the intended account outside the sandbox.
- Application scaffolding and real authentication remain outstanding. Day 1 is not complete.

## Day 1, step 2: initial FastAPI backend

- Connected `origin` to the user's confirmed GitHub repository.
- Created `backend/.venv` using Python 3.14.2 and installed FastAPI 0.143.1 and Uvicorn 0.54.0.
- Recorded installed dependency versions in `backend/requirements.txt`.
- Created `backend/app/main.py`, its package initializer, and the beginner setup/code explanation in `backend/README.md`.
- Implemented `GET /api/health`, returning `{"status":"ok"}`. This is an API availability check, not a database check.
- Verification: `python -m pip check` passed; the local virtual environment remains ignored by Git.
- Started Uvicorn temporarily on `127.0.0.1:8001` and verified real HTTP responses: `/api/health` returned 200 and the expected JSON, `/docs` returned the Swagger UI page, and `/openapi.json` documented the health endpoint.
- Stopped the verification server after checks. The user can start their development server on port 8000 using the documented command.
- No commits or pushes yet; Day 1 still requires React and real authentication.

## Day 1, step 3: React frontend and API connection

- User verified the backend startup manually and requested the next step.
- Created `frontend/` with React 19.3.1, React DOM 19.3.1, Vite 8.3.4, and the React Vite plugin 6.1.2; exact versions are recorded in the manifest and lockfile.
- Created a beginner-friendly connection page with responsive CSS, keyboard focus styling, a skip link, and an announced status message.
- The connection button calls `GET /api/health`, checks HTTP status and the JSON health status, and handles loading, success, and failure. Requests have a five-second timeout.
- Configured Vite on `127.0.0.1:5173`, with `/api` forwarded to `127.0.0.1:8000`; no backend CORS changes were needed for this local development arrangement.
- Verification: `npm run build` passed.
- Browser verification: the connection button displayed success with the existing user-run FastAPI server. Temporarily pointing the proxy at unused port 8001 displayed the unavailable message. Restored port 8000 and verified success again. The user's backend was not stopped or changed.
- Inspected the rendered layout at the browser's 509px width; page width matched the viewport with no horizontal overflow. Final browser warning/error log was empty after restoring the working connection.
- Added `frontend/README.md` explaining the files, state, HTTP request, development proxy, and two-terminal startup workflow.
- The Vite server used for verification was stopped after checks. The user can start it with `npm run dev`; reuse any existing FastAPI server on port 8000.
- Authentication, the final Day 1 review, commit, and push remain pending. No Day 2 work has started.

## Day 1, step 4: custom PostgreSQL authentication

- User explicitly approved FastAPI + PostgreSQL authentication instead of Clerk/Supabase. Supabase integration was not installed or implemented.
- Confirmed the existing local PostgreSQL 14.21 service and created separate `cab_booking_dev` and `cab_booking_test` databases with a dedicated `cab_booking_app` login. Existing databases were not modified.
- Generated ignored local database credentials and a JWT signing secret in `backend/.env` with owner-only permissions; committed examples contain placeholders only.
- Implemented SQLAlchemy user/session tables, Argon2 password hashes, registration/login, an HTTP-only signed JWT cookie, protected user/session endpoints, and PostgreSQL-backed logout revocation.
- Enforced issuer/audience/expiry/required claims and stored-session validity. State-changing authentication requests require an explicitly allowed origin. Secure cookies are the default; local `.env` opts out only for HTTP development.
- Added input validation, lowercase email uniqueness, bounded password length, public response schemas, and validation-error input redaction.
- React now supports signup, login, page-reload session restoration, protected-session verification, and logout without storing tokens in localStorage.
- Browser verification passed using a generated local demo account: signup, protected-session verification, page reload, sign-out, wrong-password rejection, and successful sign-in again. The demo account is test data in the development database, not a real user.
- Final real-PostgreSQL authentication suite: `python -m pytest -q` passed all 24 tests. One TestClient/HTTPX compatibility deprecation warning remains, as documented in the authentication walkthrough.
- Final frontend production build: `npm run build` passed after all frontend changes.
- Reviewed all 30 candidate source/documentation files for the actual generated database password and JWT secret: neither is present. Verified local credentials, virtual environment, node_modules, and build output are ignored, and `.env` has owner-only permissions.
- Signed out the generated browser demo account after verification. Its random password was not written to source or documentation.
- See `docs/AUTHENTICATION.md` for the step-by-step flow, setup, endpoints, files, testing, and current scope.
- Remaining Day 2 work is untouched: PostGIS, driver/ride/payment/review models, and Alembic migrations.

## Day 2: models, PostGIS, and migrations

- The user requested the next day after Day 1 completion. Local `main` and `origin/main` matched the previously verified Day 1 documentation checkpoint `93318c0da7e3ae4b47648dcebc57bc6296034e64` before starting.
- Retained the existing PostgreSQL 14.21 service. Compiled and installed PostGIS 3.6.4 core for it, after verifying the official source checksum. Enabled the extension only in `cab_booking_dev` and `cab_booking_test`; no service restart or other project database migration was performed.
- Installed GEOS/PROJ/libxml2/pkgconf and their Homebrew dependencies. Restored the missing version-specific PostgreSQL 14 header link. Details and build reproduction notes are in `docs/DATABASE.md`.
- Added Alembic 1.20.0 and GeoAlchemy2 0.20.0 with recorded production dependency versions.
- Added driver, ride, payment, and review models, plus optional user profile fields, rating defaults, and timestamps. Money uses Decimal/NUMERIC; points use geometry(Point, 4326) with GiST indexes.
- Added foreign keys, bounded coordinate/rating values, non-negative money/distance/duration values, and duplicate payment/review protection. Business-flow APIs remain on their scheduled days.
- Introduced `0001_auth_baseline` and `0002_booking_models`. The baseline validates an existing unversioned auth schema before adopting it and also supports fresh databases. It rejects column/key/index/constraint drift.
- Applied the development migrations and compared all original user fields and session rows before/after: preserved the existing 1 user and 2 sessions unchanged.
- `alembic current` reports `0002_booking_models (head)`; `alembic check` reports no new upgrade operations.
- Full backend suite: 43 tests passed, with the previously documented TestClient/HTTPX deprecation warning. Coverage includes auth regressions, spatial distances/indexes, data constraints, migration round trips, existing-account preservation, schema-drift refusal, and offline SQL output.
- Final targeted migration checks: all 5 passed after explicitly testing successful adoption of an unversioned Day 1 schema. Database status output now recognizes geometry columns without reflection warnings.
- Tests now initialize schema with Alembic. Migration downgrade checks are confined to the dedicated test database and rolled back; the development database was not downgraded.
- Replaced the old auth `create_all` initializer with an Alembic compatibility command. Added a safe database status command and beginner walkthrough; frontend code and Day 3 APIs were not changed.
- Day 2 implementation commit `4ae8200b1345a202c18a4ab4ea2296f3e9a82030` was pushed; `git ls-remote` returned the same SHA.

## Day 3: routing, fare estimates, and ride requests

- User requested the next milestone and chose a free alternative to Google Maps. Implemented OSRM/OpenStreetMap routing without an API key; no paid account or Google service was configured.
- Confirmed the previous Day 2 documentation commit `af94813132f8a08456d8ed90062d29cd730fe701` matched the remote before implementing Day 3.
- Added authenticated rider-only fare estimates using real driving distance/duration, validated coordinates, bounded upstream requests, short caching, and one new request per second per process. Visible attribution and coordinate-transmission disclosure accompany the form.
- Added configurable illustrative INR pricing with Decimal rounding, five-minute signed quotes bound to the rider, and audience separation from session tokens. Requests accept the signed quote rather than trusting a submitted fare or rider ID.
- Added Alembic revision `0003_ride_quote` and unique quote IDs for duplicate-request protection. Existing rides may retain null quote IDs. Applied the development migration; Alembic check reports no drift.
- Added ride request creation and owned status endpoints; other riders cannot inspect a ride and driver accounts cannot book. No driver matching or trip dispatch is implemented in this milestone.
- React now shares authenticated user state, accepts coordinates or an explicit Delhi sample, shows fare breakdown/expiry, submits the quote, displays the saved ride, and refreshes status.
- Automated verification: all **71 backend tests passed**, frontend production build passed, and pip dependency consistency check passed. One existing TestClient/HTTPX compatibility deprecation warning remains.
- Live API verification: real OSRM Delhi route returned 3,982 meters, 396 seconds, and sample fare ₹104.38. Ride creation returned 201; repeating the quote returned 200 with the same UUID; owned status returned 200; after logout it returned 401. A synthetic local demo rider and requested ride remain as development test data.
- UI verification limitation: browser URL policy rejected automated preview reload. The user answered “I haven’t tried it yet” to the manual flow check. The new form is build-verified but visual/manual behavior is unverified; keep this follow-up visible for later manual/UI testing.
- Setup, code explanation, service limitations, and the manual walkthrough are in `docs/RIDE_BOOKING.md`.
- Source review: actual local database passwords and JWT secret are absent from all 24 changed/new files. `.env` remains owner-only and ignored; virtual environment, dependencies, and frontend build output are ignored. `git diff --check` passed.
- Day 3 implementation commit `ef48c41770db6eedb4392f350176f9fb379049ec` was pushed; `git ls-remote origin refs/heads/main` returned that exact SHA. Day 4 has not started.

## Day 4: driver dashboard, availability, and matching

- The user requested the next milestone and explicitly selected “Include Day 4 (recommended).” Verified the Day 3 documentation checkpoint `8d59f1c5b04fcf3687beba196e58d2b6c57f29aa` against GitHub and confirmed a clean working tree before beginning.
- Added driver-only owned vehicle setup and online/offline endpoints. Online requires a valid vehicle and explicit coordinates; offline clears the matching location. Locations expire after five minutes by default and require an explicit refresh.
- Added PostGIS geography radius filtering (default 5 km), nearby-driver candidates for owned rider requests, and sorted nearby offers for drivers. Stale, offline, busy, and declining drivers are excluded. Candidate responses omit exact driver points and account emails.
- Added accept/decline endpoints. Acceptance locks driver then ride, rechecks eligibility, assigns a single winner, and returns the same assignment on an owned retry. Declines persist per driver/request and do not hide requests from other drivers.
- Migration `0004_driver_matching` adds location timestamps, geography expression indexes, `ride_declines`, and a partial unique index preventing multiple active rides for one driver. Applied to development; Alembic check reports no drift. Existing Day 3 data preservation is tested.
- Added the React driver dashboard and rider nearby list. Rider sign-in restores the latest open ride; driver sign-in restores the profile and active assignment. Updates use explicit refresh controls; Day 5 realtime has not started.
- Verification: **91 backend tests passed**, React production build passed, and pip check passed. Separate-connection concurrency tests verify exactly one winner for two drivers/one ride and one driver/two rides; committed synthetic test fixtures are cleaned up. One existing TestClient/HTTPX deprecation warning remains.
- Live local API demo passed: synthetic rider/driver registration, vehicle setup, online location, real OSRM estimate, persisted ride, nearby candidate at 12 meters, offer/acceptance, same-ride repeat acceptance, rider/driver restoration, offline location clearing while retaining assignment, and logout revocation. Demo ride `cde03821-ad85-4f26-8958-7cb2141e615e` is accepted; its synthetic driver was left offline. These records are local development test data.
- Preview HTTP response: 200. Automated visual interaction remains unverified because of the earlier browser URL-policy rejection. The user answered “I haven’t tried it yet” to the manual driver-dashboard check. Day 3's full manual UI flow also remains unverified.
- Known scope: demo matching permits clearly labeled unverified drivers; geographic matching distance is not a road ETA; location presence is explicit rather than tied to browser login; active ride progression/completion and realtime remain later work.
- Beginner setup and two-account steps are in `docs/RIDE_MATCHING.md`.
- Source review: actual local database passwords and JWT secret are absent from all 23 changed/new files. `.env` remains ignored and owner-only; dependencies, virtual environment, and generated build output remain ignored. `git diff --check` passed.
- Day 4 implementation commit `834ae6e413fadb6a5e1c61a2c66d0d19191fe5b9` was pushed; `git ls-remote origin refs/heads/main` returned that exact SHA. Day 5 remains optional and has not started.

## Day 5: realtime notifications, locations, and trip status

- The user selected “Include Day 5 (recommended).” Verified Day 4 documentation checkpoint `1af381c19bcabe7bc2c46e5d93803022e5dbd3e1` against GitHub and confirmed a clean working tree before starting.
- Reused the existing local Redis 8.6.0 service on 6379 without restarting/reconfiguring it or modifying unrelated keys. Added pinned Python `redis==8.1.0` and `websockets==17.2` dependencies.
- Added `/api/ws/rider/{user_id}` and `/api/ws/driver/{user_id}` via a role-validated route. The `/api` path preserves the HTTP-only cookie scope. Origin, token, stored session, account ID, and role are checked; connected sessions are rechecked before events/messages and every two seconds while idle.
- Redis carries account-scoped ride/driver invalidations plus a generic matching signal containing no IDs/coordinates. Publishing follows committed PostgreSQL writes and catches broker failures without reporting a saved write as failed. Short database sessions, bounded sends, task/subscription cleanup, and namespaced channels support multiple workers.
- Added location messages with acknowledgements, HTTP fallback, online requirement, validation, and one-second update spacing on the dedicated location paths. Only the assigned rider can read a fresh point; offline/stale/finished rides expose none.
- Added guarded assigned-driver progression `accepted → arriving → in_progress → completed` with same-step retries and no skipping/regression. Completion releases the active assignment and does not charge a payment or set `fare_actual`; Day 6 remains untouched.
- React shows connection state, reconnects with capped backoff, coalesces notifications, and rereads protected API snapshots. Ready/reconnect and periodic 15-second sync recover missed Pub/Sub events. Refresh controls remain, unsaved form inputs are preserved, and stale responses/old sockets are guarded during account changes.
- Final verification: **113 backend tests passed**, React production build passed, Alembic check reported no drift, and pip check passed. Schema remains `0004_driver_matching`. One existing TestClient/HTTPX deprecation warning remains.
- Integration tests use real temporary TCP WebSocket servers, Redis with unique test prefixes, and the guarded PostgreSQL test database. They cover Origin/account/role/token rejection, private-channel isolation, location/status delivery, validation/freshness/throttling, logout/JWT expiry on open sockets, oversized messages, broker outage, reconnect recovery, and coherent concurrent location reads. Synthetic committed fixtures are removed; Redis is not flushed.
- Live development demo passed: Vite WebSocket forwarding, REST writes on 8000 delivered through Redis to a rider socket on independent backend 8002, location sharing, all trip steps, hidden completed-ride location, and logout closure. Synthetic ride `77e46024-c667-4715-8090-10bc73ada350` is completed; its driver was left offline. Local demo records remain development test data.
- Preview HTTP response: 200. Automated visual interaction remains unverified after the earlier browser URL-policy rejection. User answered “I haven’t tried it yet” to the manual live-connection-badge check. Prior full rider/driver UI checks remain unverified too.
- Setup, code/protocol explanations, security boundaries, and the two-window walkthrough are in `docs/LIVE_UPDATES.md`.
- Source review: actual local database passwords and JWT secret are absent from all 28 changed/new files. `.env` remains ignored and owner-only; dependencies, virtual environment, and build output remain ignored. `git diff --check` passed.
- Day 5 implementation commit `4a99f39759ec485565597b570a02b6866006530d` was pushed; `git ls-remote origin refs/heads/main` returned that exact SHA. Day 6 payments have not started.

## Day 6: test payments (code checkpoint; provider checks deferred)

- User requested the next milestone and then asked to continue. Verified Day 5 documentation checkpoint `0d465f99e1c8585741f9d610add7dd63f3258422` against GitHub and confirmed a clean working tree before starting.
- Added pinned Stripe Python SDK 16.0.0 and its dependencies, plus official React Stripe.js 7.0.0/Stripe.js 10.1.0 packages. No account or sandbox has been created; no Git identity has been sent to Stripe.
- Added completed-ride owner-only invoices, final-fare freezing from stored data, stable PaymentIntent idempotency, canonical provider checks, and locked concurrent retries. Unlinked invoices older than 23 hours require reconciliation before recreation beyond Stripe's idempotency window.
- Added raw-body webhook signature verification, test-only mode checks, bounded bodies, canonical intent retrieval, amount/currency/metadata validation, atomic event-ID deduplication, and terminal-state protection. Browser confirmation alone cannot mark an invoice paid.
- Migration `0005_test_payments` adds currency/timestamps and `payment_events`. Applied to development; Alembic check reports no drift. Existing payment preservation, fresh upgrades, and rollback migrations are tested in the separate test database.
- Added React Payment Element for completed rides, lazy Stripe.js loading, safe client-secret handling in component state, provider-error/status display, and realtime/manual invoice refresh. Latest completed ride is recoverable after reload when no open ride exists.
- Added optional test-key settings with live-key rejection and `scripts.configure_test_payments` for hidden local entry into ignored `.env`. The helper has not been run with actual credentials.
- Verification: **144 backend tests passed**; pip consistency and React production build passed. Payment API calls use a controlled provider double; official Stripe objects/signature verification and real PostgreSQL concurrency are tested. One existing TestClient/HTTPX warning remains.
- Local HTTP smoke check passed with a synthetic rider: frontend/health 200, config reports `configured=false`, checkout 503 without keys, unsigned webhook 400, logout followed by config 401. No Stripe transaction was attempted; a synthetic local configuration-demo account remains development test data.
- Real-provider/rendered-checkout verification remains pending. Stripe secret/publishable/webhook keys were absent at the start; setup choices have been requested. Creating a temporary sandbox using the user's Git identity requires that user's explicit selection. No approval has been inferred from elapsed time.
- Earlier browser URL-policy rejection still prevents automated visual checking; no new browser pass is claimed. Follow the setup and success/decline/retry walkthrough in `docs/PAYMENTS.md`.
- Final source review repeated for the deferral checkpoint: local database passwords and signing secret absent from all 33 changed/new files; Python syntax and whitespace checks passed. `.env` remains ignored with mode 0600; helper temporary configuration names and generated/dependency folders are ignored.
- Stopped the temporary backend and React preview after HTTP checks; existing PostgreSQL and Redis services were not stopped. Restart commands are in the payment walkthrough.
- On 2026-10-18 the user asked to do Stripe setup later and continue to the next day. Recorded this explicit exception in `AGENTS.md`, the roadmap, and payment walkthrough. No account, sandbox, or credentials are needed for Day 7's local checks; real-provider and rendered-checkout checks remain deferred.
- Repeated checkpoint verification: 144 backend tests passed in 13.38 seconds, React production build passed, pip check passed, and Alembic reported no new upgrade operations. The existing TestClient warning remains; these checks do not verify Stripe delivery or rendered checkout.
- Day 6 code commit: `d2e9e778969be525ee5ff1a7983b1e185ffbf63d`; push succeeded and GitHub `refs/heads/main` matched exactly. Day 7 may proceed under the user's explicit deferral; this does not close the outstanding Stripe verification.

## Day 7: first-week testing (checkpoint verified; follow-ups tracked)

- Began only after the Day 6 code checkpoint was pushed and verified, with a clean working tree. No Day 8 work is included.
- Added `backend/tests/test_week_one_flow.py`: one connected endpoint journey creates rider/driver accounts, estimates/books/retries a ride, matches a driver, rejects skipped progression, completes the trip, checks driver release, restores the rider after login, rejects disabled checkout without an invoice/final-fare write, prioritizes a new open request, and rejects replay of a logged-out session.
- The new journey uses migrated PostgreSQL/PostGIS, real API registration/login, and rollback isolation. Routing metrics are controlled, notifications are silenced, and a sentinel payment adapter rejects accidental provider calls. Actual Redis/TCP behavior is covered by the existing realtime suite; this journey is not a real provider or browser test.
- Verification: the new journey passed in 0.88 seconds; the complete suite then passed all 145 tests in 12.96 seconds. No new application bug was observed or production-code fix required. React build, pip consistency, and schema drift checks passed immediately before the test/documentation-only Day 7 changes; they were not needlessly repeated. The existing TestClient warning remains.
- Added `docs/TESTING.md` explaining the commands, test boundaries, manual two-account checklist, and follow-ups. Browser rows remain pending rather than being marked passed from API results.
- Known follow-ups: user-deferred Stripe setup/real sandbox payment/signed provider webhook/rendered checkout, pending Day 3-5/manual browser flows, and the existing TestClient/HTTPX deprecation warning. Day 7 can track these explicitly as allowed by the roadmap; it does not claim them resolved.
- Source review: Python syntax, local documentation links, absence of actual local credentials in all five changed/new files, and whitespace checks passed. Day 7 changes contain tests and documentation only.
- Day 7 implementation commit: `4746d1750d948db614feca1619a552a3e22a41fc`; push succeeded and GitHub `refs/heads/main` matched exactly. Day 8 has not started.

## Day 8: history and receipts (implementation checkpoint verified)

- User requested the next milestone. Verified local HEAD and GitHub `refs/heads/main` both equal Day 7's final documentation checkpoint `f415d80e2dbeacfcd8c4666818a5e818e3276ea9` before starting; working tree was clean.
- Rechecked the mentor's Day 8 requirements: history endpoints, WeasyPrint PDF receipts and Celery email tasks. Added pinned Celery 5.6.3, WeasyPrint 70.0 and runtime dependencies; pinned PDF-extraction/loopback-catcher dependencies are development-only. Existing package versions remain unchanged.
- Installed Pango 1.58.2 with Homebrew and its native dependencies; Homebrew updated/cleaned required library dependencies as part of installation. Existing PostgreSQL and Redis services were not restarted or reconfigured. On this Mac, Python needs `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` before startup; documented for API, worker and tests. Initial native import failed without it and then passed with it.
- Added role/participant-owned completed/cancelled history, bounded stable `(created_at, id)` cursor pagination, payment summaries and private completed-trip PDF downloads. No fare/payment state is changed by downloads. Unpaid trips produce explicitly unpaid trip statements; succeeded test ledger entries produce test receipts.
- WeasyPrint renders escaped server-owned fields with external/file resource fetching denied. No arbitrary HTML, recipient, amount or template is accepted. PDF includes only trip participant names and trip/payment details, without account emails/passwords/provider secrets.
- Applied Alembic `0006_receipt_emails` to development; no schema drift. Durable job snapshots/fingerprints deduplicate repeated requests per participant/document; changed payment data creates a new version. Job IDs alone cross Redis. Saved jobs survive publication failure for explicit republishing; no automatic outbox sweep is claimed.
- Added Celery worker with its own DB sessions, job row locks, duplicate skipping, three bounded attempts, a one-minute failed-job manual retry cooldown and ten-second SMTP I/O timeout. Stable Message-ID does not guarantee exactly-once SMTP delivery across a crash before DB commit; this limit is documented. Sent means accepted by SMTP, not inbox delivery.
- React adds paginated history for both roles, protected PDF downloads, explicit email request/status controls and older rider payment details. Email remains disabled in ordinary local configuration; the documented local catcher never forwards messages externally. No actual external email provider is configured or tested.
- Verification: **157 backend tests passed in 19.80 seconds**, including 12 new history/PDF/job/local-worker checks. A real Celery subprocess consumed duplicate copies over uniquely namespaced Redis, the loopback SMTP catcher accepted one message/PDF attachment, and PostgreSQL recorded sent with one attempt. Synthetic committed test rows and only the test's Redis keys were removed; no Redis flush occurred.
- React production build passed (28 modules); pip check and Alembic drift check passed. Migration upgrade/downgrade and existing-account/invoice preservation tests passed at the new head. One existing TestClient/HTTPX deprecation warning remains.
- Generated an ignored synthetic unpaid PDF, rendered it to PNG using Poppler and visually inspected the one-page layout: readable text, correct amount/status, and no clipping/overlap. New PDF content tests cover paid amount selection, escaping, completion/ownership guards and private response headers.
- Browser interaction remains unverified after the earlier URL-policy rejection; no workaround or visual React pass is claimed. Manual history/download/email follow-up is recorded in `docs/HISTORY_RECEIPTS.md`. Earlier Day 3-5 manual checks and the user-deferred real Stripe checks remain pending.
- Source review: Python syntax, local documentation links, whitespace and absence of actual local credentials passed for all 26 changed/new files. Existing runtime version pins are retained; private `.env` remains ignored with mode 0600, and generated samples/dependencies/build output remain ignored. All test-owned worker/SMTP/socket processes were cleaned up; no development preview server was started in this milestone.
- Day 8 implementation commit: `f70387c95fbf4e69736a3a7ee6b41f6c875da426`; push succeeded and GitHub `refs/heads/main` matched exactly. Day 9 has not started.

## Day 9: ratings and reviews (implementation checkpoint verified)

- User requested the next milestone. Verified local HEAD and GitHub `refs/heads/main` both equal Day 8's final documentation checkpoint `9f59017d2d4d39453aefb2a1fcd6f0c0e3a61e2f`, with a clean working tree before starting. No Day 10 work is included.
- Added participant-only review reads/writes for completed rides and own rating summaries. Recipient and author come from the stored ride/session; client-supplied identity fields are rejected. Completed trips do not require payment to be reviewed, so the user's Stripe deferral does not block this feature.
- Ratings require strict integers 1-5; comments are trimmed, blank-to-null, at most 2,000 characters, valid Unicode without NUL, and returned/displayed as plain text. Errors omit submitted comment text. Unrelated accounts get 404; anonymous/revoked sessions and forbidden Origins are rejected by existing protections.
- Existing `(ride_id, rater_id)` uniqueness is retained. First submissions return 201; identical normalized retries return the original review with 200; conflicting changes return 409. No review editing/deletion is introduced.
- Review insert and recipient `users.rating_avg` update commit together. Trip row locks serialize duplicate submissions; recipient `FOR NO KEY UPDATE` locks serialize averages across trips while permitting foreign-key key-share checks for opposite-direction reviews. Summary average/count are read in one SQL aggregate statement and rounded half-up to two decimals; no reviews returns null/zero rather than a zero-star score.
- Applied migration `0007_review_timestamps`: old review text/IDs/ratings remain, unknown old dates stay null, new inserts default to server time, and derived user averages are reconciled. Identity/password/session/ride/invoice data are preserved. New legacy-preservation and existing migration tests passed; Alembic reports no drift. No package or configuration secret was added.
- Added `RideReviews` controls and own rating summary in history. Live/manual reads show saved and received reviews; comments render as React text. Background history refresh no longer unmounts open review/payment forms, avoiding draft reset on periodic live sync. Browser interaction is not claimed verified.
- Added private `review.changed` notifications for the two trip participants after commit, containing only type/ride ID. Real Redis/TCP checks verify delivery, no matching-channel publication, minimal payload projection and unrelated-account rejection. Existing fixture cleanup now removes synthetic reviews before their parent rides.
- Verification: **184 backend tests passed in 22.89 seconds**, including 27 new review/validation/migration/notification checks and five concurrent-write scenarios. Pip consistency and Alembic drift checks passed. Earlier targeted runs (29 review/migration, 46 review/realtime) and the initial 182-test run also passed; the final run adds two invalid-comment text cases. One existing TestClient/HTTPX deprecation warning remains.
- React production build passed (29 modules). Manual review-form/summary/reload/draft-preservation checks remain pending under the earlier browser URL-policy rejection. Stripe real-provider/rendered-checkout checks remain user-deferred; external email remains unconfigured.
- Final source review: all 25 changed/new candidates passed Python syntax, local document-link, whitespace and actual-credential absence checks. Private `.env` remains ignored with mode 0600; generated/dependency output remains ignored. No dependencies were added or updated. Test-owned TCP/worker/SMTP resources were cleaned up; existing PostgreSQL and Redis services were not changed.
- Walkthrough, payloads, lock/aggregation explanation, migration behavior and manual steps are in `docs/REVIEWS.md`. Day 9 implementation commit `90bc586f9690772e0cac78654cb73a5d73305a76` was pushed successfully and GitHub `refs/heads/main` matched exactly. Day 10 has not started.

## Day 10: promo codes and test-wallet top-ups (implementation checkpoint verified)

- User requested the next milestone, then continued the active work. Local HEAD and GitHub `refs/heads/main` matched Day 9's final documentation checkpoint `2bd51f92f28fc3dc40877991207d9ca22ba1dc9c` with a clean working tree before starting. The earlier Stripe setup/real-provider deferral is carried forward explicitly.
- Added completed-trip rider-only promo application before invoice creation, normalized code validation, active dates, capped percentages, minimum fares and global/personal usage limits. A unique immutable redemption snapshots before/discount/final amounts, and the saved actual fare feeds later checkout/PDFs. Identical retries return the existing snapshot; stacking/removal and changes after invoice creation are rejected.
- Added Alembic `0008_promos_wallet`: zero-default balance, promo rules/redemptions, top-up request UUIDs, unique credit ledger and an exactly-one-target extension to the global Stripe event audit. Upgrade applied to development with no schema drift. Migration tests preserve existing ride payment/events and explicitly exercise destructive wallet-data downgrade only within a rolled-back test transaction.
- Created `WELCOME10` locally: 10% capped at INR 50, minimum INR 80, one use/rider, 100 total, valid 30 days. Rerunning the seed preserved the existing code/rules/expiry. No public promo-management API or synthetic development wallet credit was added.
- Added rider wallet reads, bounded INR 50-10,000 test top-up creation/retry and owned resume/status. Durable user/request UUIDs and provider idempotency keys survive response uncertainty. Old unlinked attempts are refused for reconciliation. Browser/provider responses cannot credit balances.
- Reused raw-body Stripe SDK signature verification and shared canonical test-intent checks for ID, amount/received amount, currency and owner/project/kind metadata. One transaction records the event, unique credit, balance and success time; top-up/user locks prevent duplicate/lost concurrent credits. Terminal state cannot regress. No actual Stripe provider call or charge was used in tests.
- Added React promo and wallet panels, reuse of the test-card form, saved attempt retry/resume, recent credits, private `wallet.changed` refresh and manual fallbacks. Missing Stripe configuration disables top-ups while allowing balance reads/promos. Manual browser interaction remains unverified.
- Added discount rows to PDF snapshots. Rendered and visually inspected the synthetic INR 104.38 -> INR 10.44 discount -> INR 93.94 unpaid statement as one readable page, retaining its not-proof-of-payment notice. Existing unpromoted receipt fingerprints remain stable.
- Review found a receipt race: a promo committed after the caller loaded the ride could display a new discount with the old total. A two-session regression reproduced that failure. Snapshot generation now refreshes and reads ride, invoice and redemption in one database statement; the regression passes without holding a ride lock through PDF rendering.
- Final checks after that fix: **230 backend tests passed** (28.01s) with the existing TestClient/HTTPX deprecation warning; React production build passed; `pip check` found no broken requirements; `alembic check` found no new operations. Tests include eight separate-connection concurrency scenarios for promo retries/limits/invoice races and wallet retries/duplicate or distinct events/different top-ups, plus real Redis/WebSocket private notification checks.
- New beginner walkthrough: `docs/PROMOS_WALLET.md`. No new dependency or secret introduced. Actual Stripe ride/top-up sandbox transactions, real signed deliveries and rendered checkout remain deferred. Wallet spending, withdrawals, refunds and automated reconciliation are outside this milestone. Day 11 has not started.
- Final source review: actual local credentials absent from all 29 changed/new candidates; Python syntax, local Markdown links and whitespace checks passed. Private `.env` remains owner-only; local environment/dependencies/build output and sample PDFs remain ignored.
- Day 10 implementation commit `561181c9b33fadc1f68df01609abee66b3d56ca8` was pushed successfully; local HEAD and GitHub `refs/heads/main` matched exactly and the working tree was clean before this completion-record edit. Day 11 has not started.

## Day 11: UI polish, accessibility and responsiveness (code checkpoint verified; manual checks pending)

- User requested the next milestone. Verified local HEAD and GitHub `refs/heads/main` both match Day 10's final documentation checkpoint `5c93b7278c90ebb86568a7d58d176b8334152beb`; working tree was clean before starting. No Day 12 work is included.
- Added named native section links and focusable targets, role-aware driver/rider copy/checklists and a clear test-project label. Moved the connection checker into a native disclosure. Rider booking/wallet panels use a wide-screen grid, retain DOM reading order and stack at narrower widths.
- Improved header/navigation wrapping, zero-minimum grid tracks, long-reference wrapping, nested panel padding, mobile action rows, 16px form inputs, explicit control colors and 44px minimum button/disclosure/rating-label targets. Preserved visible focus outlines and added forced-colors highlight styling. Rendered reflow/target sizes are not claimed as measured.
- Added account heading/error focus after explicit actions without moving focus during passive restore. Added wallet/comment hints and short live balance announcements. Repeated current/history `RidePayment` instances now use unique IDs and correct label targets. History has per-trip headings/action groups, disclosure state and named pagination.
- Added exact development-only test dependency pins and a separate Vitest/jsdom configuration. Initial install encountered an existing npm-cache permission error; retried with a separate temporary cache and left user cache ownership/permissions untouched. The successful install audited 99 packages with zero vulnerabilities. Production dependency and Vite pins are unchanged.
- Final focused component checks: **9 passed**. Fixtures cover guest/rider/driver structures, valid/unique label and ARIA targets, selected axe WCAG-tagged rules, first Tab stop, account mode keyboard activation, successful sign-in/logout focus, failed sign-in error focus/email retention, duplicate trip payment panels, promo keyboard submission with Stripe disabled, and native review arrow keys/draft preservation/numeric submission. HTTP and realtime are controlled fixtures; no browser/backend/payment service was contacted.
- React production build passed (30 modules; JS 288.91 kB, gzip 87.60 kB). Source palette calculations checked representative opaque pairs, including muted text at 5.50:1 on the page and 5.22:1 on fare panels; strengthened the decorative step-number shade from 4.34:1 to the muted shade. These are calculations, not rendered contrast/layout evidence. No backend or schema change; Day 10's 230-test result remains the last backend run.
- Asked for manual desktop/phone-width/Tab checks while continuing independent work. No answer or visual pass is recorded yet. Earlier browser automation policy rejection was respected; no new browser automation/workaround attempted. jsdom excludes painted color contrast and does not verify layout, zoom, focus appearance, screen-reader behavior or Stripe iframes. No WCAG conformance claim is made.
- Added `docs/UI_POLISH.md` with files, commands, explanations, verification boundaries and the pending manual checklist. Real Stripe checks remain user-deferred. Day 12 has not started.
- Final source review passed for all 20 changed/new candidates: actual local secrets absent, JSON and local Markdown links valid, whitespace clean, no backend files changed and ignored private configuration/dependencies/build outputs remain untracked. `.env` retains owner-only permissions.
- Day 11 code commit `a8bf1f87adf641d58e422e0683070843622a16cb` was pushed successfully; local HEAD and GitHub `refs/heads/main` matched exactly and the working tree was clean before this completion-record edit. Manual review remains unresolved; Day 12 has not started.

## Day 12: request protection, validation and query performance (implementation checkpoint verified)

- The user repeatedly requested the next milestone after the Day 11 manual-review reminder. Continued with those checks pending; no tested-UI answer or browser pass is inferred. Local HEAD and GitHub `refs/heads/main` matched Day 11's final documentation checkpoint `caf8c1af22dec626aade98455052b5237d6327cf` with a clean working tree before starting.
- Added shared fixed-window Redis quotas using an atomic multi-bucket Lua script with bounded timeouts/no retries, HMAC key identities, TTLs, 429/Retry-After and explicit 503 on protection failure. Middleware groups peer quotas; login separately checks normalized email before password work. Quotas cover API reads/writes, auth, estimates, checkout and documents. Health and signed Stripe delivery retain documented exceptions; no Redis data was flushed.
- Added per-peer WebSocket handshake quotas and a bounded rolling incoming-message window. Existing session/Origin/privacy/location/message-size checks remain. Real TCP flood testing closes the socket with 1008; Redis handshake failure follows the 1013 path. No total concurrent-connection limit is claimed.
- Added actual/declared/chunked request size checks, a ten-second body read bound, JSON media enforcement, safe no-store/nosniff/referrer/frame headers and strict explicit CORS with GET/POST/PUT and credentials. Preserved the receipt's private/no-store header after the full suite exposed an overbroad initial replacement. Updated local startup commands to `--no-proxy-headers`; production trusted-edge setup remains Day 14 work.
- Authentication rejects unknown fields; coordinates require finite numeric values and no extras; names/vehicle text reject NUL/invalid Unicode before PostgreSQL/JSONB. Existing password/input redaction and ownership checks are preserved.
- Added `0009_query_indexes`: two partial ordered history indexes, two ordered wallet indexes and one promo/user composite, replacing three redundant single-column indexes. Development upgrade fingerprinted every row across all 13 application tables before/after: unchanged. Alembic reports the new head with no drift; no development downgrade was run.
- Removed driver-offer coordinate N+1 queries by selecting and reusing coordinates in the nearby-offer query. A regression returned 20 offers with one coordinate-bearing statement; other authorization/profile reads remain.
- Real PostgreSQL query plans on a rolled-back `_test` fixture (4,000 rides, 2,000 top-ups and 2,000 credits) selected all four history/wallet indexes without sort nodes, preserving returned rows and balance through upgrade/downgrade. Warm-cache shared-hit blocks: rider history 3 -> 3, driver history 86 -> 3, wallet entries 24 -> 3, top-ups 31 -> 3. These fixture-specific observations are not production performance guarantees.
- Final backend suite: **263 passed in 32.79s**, with the existing TestClient/HTTPX deprecation warning. Thirty new security cases cover actual Redis concurrency/expiry/atomic denial, rate/Origin/CORS/body/input/config boundaries and failure behavior; further regressions cover frame flooding, offer-query count and migration/query plans. Existing business-flow suites isolate quotas; dedicated limiter tests use real Redis with scoped key cleanup.
- React component suite: **9 passed**; production build passed. Pip consistency and schema checks passed. No new dependency/package pin was introduced. Documentation is in `docs/SECURITY_PERFORMANCE.md`. Manual UI and user-deferred actual Stripe verification remain pending. Day 13 has not started.
- Final source review passed across 36 changed/new candidates: actual local secrets absent, Python syntax/local Markdown links valid and whitespace clean. Local `.env` remains owner-only; configuration, dependencies, generated builds and sample PDFs remain ignored. Frontend feature code is unchanged.
- Day 12 implementation commit `713017c28dc3812adcecabd765cddd381e23cf35` was pushed successfully; local HEAD and GitHub `refs/heads/main` matched exactly and the working tree was clean before this completion-record edit. Day 13 has not started.

## Day 13: multiple-account API journeys (implementation checkpoint verified)

- User requested the next milestone and then continuation. Day 12's final documentation checkpoint was verified against GitHub before implementation; the same remote SHA was rechecked on 2026-10-20 when work resumed.
- Added a temporary loopback HTTP/WebSocket fixture with migrated test-database sessions, real Redis quotas/notifications and independently registered client-cookie accounts. Routing metrics and Stripe provider calls remain controlled doubles. A separate Celery worker and loopback SMTP catcher delivered the discounted paid-test PDF to the correct account; no external email was sent.
- Verified a connected two-rider/two-driver journey with a third trip after driver release, request retries, guarded progression, private/paginated history, promos/invoice/event retries, four rating summaries, one wallet credit despite distinct signed events, and rejected cross-account reads. Provider success alone leaves local payment/balance pending until the signed fixture event. Logout invalidates a replayed cookie and closes its existing socket with the existing 4401 protocol while the second rider stays signed in.
- Verified two actual HTTP accept races (two drivers/one ride and one driver/two rides): each had one 200, one 409 and exactly one assignment. Verified distant, stale and previously declining drivers cannot accept a pending request. Existing lower-level concurrency suites remain intact.
- Found that Day 12 classified fare-estimate quotas only within write methods while the estimate endpoint uses GET. A new real-Redis regression reproduced the missing 21st-request rejection (422 instead of 429). Moved estimate classification outside the write-only branch; the same regression now returns 429/Retry-After as intended. No schema or dependency change was required.
- Added two React component journeys for ambiguous booking-response recovery with the same signed quote, completed-trip payment controls, input retention after 429 and session-expiry handling after 401. These use controlled HTTP fixtures in jsdom; no browser/layout pass is inferred.
- Final complete backend suite: **268 passed in 33.27s**, with the existing TestClient/HTTPX deprecation warning. Focused journey/GET-regression set: 5 passed in 7.30s after correcting the test's expected logout close code. React: **11 passed**, production build passed. Pip consistency and Alembic no-drift checks passed; schema remains `0009_query_indexes`.
- Read-only cleanup verification found zero Day 13 journey accounts/campaigns and zero journey-prefixed Redis keys. Fixture teardown asserts the owned server thread stopped and terminates the owned worker/catcher; existing services and development records/configuration were not modified.
- Added `docs/END_TO_END_TESTING.md` with commands, real-versus-controlled service boundaries and the remaining UI/provider checks. Day 14 has not started.
- Final source review passed for all 13 changed/new candidates: actual local credentials absent, Python syntax and local Markdown links valid, whitespace clean and private/generated files remain ignored. Local `.env` retains owner-only permissions. No schema, package pin or frontend feature code changed.
- Day 13 implementation commit `97a992e7f4385b8e65f0de4889e7bd226ec09374` was pushed successfully; local HEAD and GitHub `refs/heads/main` matched exactly and the working tree was clean before this completion-record edit. Day 14 has not started.

## Daily completion record

Day 13:

- Scope delivered: multi-account API/service journeys, local PDF email, real HTTP assignment races, driver eligibility, booking-recovery component checks and the GET-estimate quota regression fix.
- Verification: 268 backend tests, 11 React tests, production build, dependency/schema consistency and owned test-state cleanup passed.
- Known limits: real OSRM/Stripe calls are controlled in the journeys, browser/manual UI and actual Stripe checks remain pending, local SMTP acceptance is not external inbox delivery, and the existing TestClient warning remains.
- Implementation commit: `97a992e7f4385b8e65f0de4889e7bd226ec09374`.
- Remote: `https://github.com/rarjun07/Cab-Booking-Platform-Python-Stack.git`, branch `main`.
- Push result: succeeded; exact remote implementation SHA verified. This record follows in a documentation commit; compare current HEAD and GitHub for the latest checkpoint.
- Ready for Day 14: after this record is pushed and verified, await the user's next instruction while retaining the pending UI/Stripe checks.

Day 12:

- Scope delivered: shared Redis quotas, bounded HTTP/WebSocket inputs, strict browser origin settings, safe response/input handling, index-only migration and fewer offer-coordinate reads.
- Verification: 263 backend tests, 9 React checks, production build, pip/schema checks, development row preservation and synthetic real-planner comparisons passed.
- Known limits: fixed windows/NAT sharing, protected-request Redis dependency, trusted proxy configuration needed at deployment, pending manual UI and actual Stripe provider checks. Existing TestClient warning remains; fixture plans do not establish production capacity.
- Implementation commit: `713017c28dc3812adcecabd765cddd381e23cf35`.
- Remote: `https://github.com/rarjun07/Cab-Booking-Platform-Python-Stack.git`, branch `main`.
- Push result: succeeded; exact remote implementation SHA verified. This record follows in a documentation commit; compare current HEAD and GitHub for the latest checkpoint.
- Ready for Day 13: after this record is pushed and verified, await the user's next instruction while carrying the pending UI/Stripe checks explicitly.

Day 11 (code checkpoint verified; manual checks pending):

- Scope delivered: existing React screen polish, responsive CSS, role-specific section navigation, account focus, form/disclosure semantics and targeted component accessibility checks.
- Verification: 9 focused simulated-DOM tests and React production build passed. Representative text palette ratios calculated. No actual browser visual/mobile/keyboard/screen-reader pass claimed.
- Known limits: manual checklist needs actual results or explicit user deferral; prior Stripe checks remain deferred. Backend unchanged; no Day 12 features added.
- Implementation commit: `a8bf1f87adf641d58e422e0683070843622a16cb`.
- Remote: `https://github.com/rarjun07/Cab-Booking-Platform-Python-Stack.git`, branch `main`.
- Push result: succeeded; exact remote implementation SHA verified. This record follows in a documentation commit; compare current HEAD with GitHub for the latest checkpoint.
- Ready for Day 12: no; resolve the actual manual review or obtain explicit user deferral first. No browser pass is claimed.

Day 10:

- Scope delivered: promo rules and frozen discounts, PDF discount details, rider test-wallet top-up retry/resume, verified-event credit ledger and private live refresh.
- Verification: 230 backend tests, React build, pip/schema checks and one-page PDF visual inspection passed. Provider requests are controlled doubles and signed event fixtures; no actual Stripe transaction is claimed.
- Known limits: user-deferred Stripe setup/real-provider/rendered-checkout checks and previous manual browser checks remain unverified. Wallet spending/refunds and scheduled reconciliation are not implemented. Existing TestClient warning remains.
- Implementation commit: `561181c9b33fadc1f68df01609abee66b3d56ca8`.
- Remote: `https://github.com/rarjun07/Cab-Booking-Platform-Python-Stack.git`, branch `main`.
- Push result: succeeded; exact remote implementation SHA verified. This completion record follows in a documentation commit; compare current HEAD and GitHub for the latest checkpoint.
- Ready for next milestone: after this record is pushed and verified, await the user's next instruction, carrying deferred provider/manual checks explicitly. Day 11 has not started.

Day 9:

- Scope delivered: rider/assigned-driver reviews after completed trips, strict/normalized comments and ratings, private reads and summaries, identical-retry handling, serialized cached-average updates, React review forms and private live notifications. Background history refresh keeps forms mounted.
- Verification: 184 backend tests passed, including five real separate-connection concurrency scenarios, legacy review/date/average migration preservation, and real Redis/TCP review-notification privacy. React build, pip consistency, Alembic drift and source checks passed.
- Source review: actual local credentials absent from all 25 changed/new candidates; syntax/document links/whitespace passed; private environment and generated/dependency files remain ignored. No new package, account or configuration secret was added.
- Known limits: review UI, reload and draft-preservation behavior remain manual browser follow-ups; earlier browser checks and user-deferred Stripe provider/rendered-checkout verification remain unverified. Reviews are immutable and available to trip participants. Administrative SQL feedback edits require explicit aggregate recalculation. One existing TestClient warning remains.
- Implementation commit: `90bc586f9690772e0cac78654cb73a5d73305a76`.
- Remote: `https://github.com/rarjun07/Cab-Booking-Platform-Python-Stack.git`, branch `main`.
- Push result: succeeded; exact remote implementation SHA verified. This completion record follows in a documentation commit; compare current HEAD with GitHub for the latest checkpoint.
- Ready for next milestone: after this record is pushed and verified, await the user's next instruction. Day 10 has not started.

Day 8:

- Scope delivered: participant-owned completed/cancelled history, private WeasyPrint PDFs, React history/download/email controls, and durable versioned Celery receipt-email jobs with status/retries.
- Verification: 157 backend tests passed, React build passed, schema upgrade/preservation/downgrade and no-drift checks passed, pip check passed, and rendered PDF sample visually inspected. Real Celery/Redis/loopback SMTP test captured one readable PDF email from duplicate queued copies and recorded one sent attempt.
- Source review: actual local credentials absent from all 26 changed/new candidates; private configuration/generated output remain ignored; syntax, document links and whitespace passed. Existing runtime version pins are retained.
- Known limits: default email remains disabled until configured; only local SMTP acceptance was verified, not an external inbox. SMTP submission/database commit cannot guarantee exactly-once delivery across a crash; lost queue publication requires explicitly requesting the saved receipt again. Browser interaction/manual UI and user-deferred Stripe verification remain unverified. One existing TestClient warning remains.
- Implementation commit: `f70387c95fbf4e69736a3a7ee6b41f6c875da426`.
- Remote: `https://github.com/rarjun07/Cab-Booking-Platform-Python-Stack.git`, branch `main`.
- Push result: succeeded; exact remote implementation SHA verified. This completion record follows in a documentation commit; compare current HEAD with GitHub for the latest checkpoint.
- Ready for next milestone: after this record is pushed and verified, await the user's next instruction. Day 9 has not started.

Day 7:

- Scope delivered: connected first-week rider/driver API journey, beginner-friendly testing guide, manual checklist, and explicit follow-up tracking. No new application feature or production-code fix was required by the observed checks.
- Verification: 145 backend tests passed, including the new journey and existing PostgreSQL concurrency/TCP WebSocket/Redis suites. React build, pip consistency, and Alembic drift checks passed immediately before the test-only changes.
- Limitations: browser checklist remains pending; Stripe setup and real provider/rendered-checkout verification are deferred by the user's explicit instruction. The existing TestClient deprecation warning remains. These items are tracked, not reported as fixed or verified.
- Implementation commit: `4746d1750d948db614feca1619a552a3e22a41fc`.
- Remote: `https://github.com/rarjun07/Cab-Booking-Platform-Python-Stack.git`, branch `main`.
- Push result: succeeded; exact remote implementation SHA verified. This completion record follows in a documentation commit; compare current HEAD and GitHub for the latest checkpoint.
- Ready for next milestone: after this documentation record is pushed and verified, await the user's instruction. Day 8 has not started.

Day 5:

- Scope delivered: authenticated FastAPI WebSockets, Redis Pub/Sub invalidations, automatic React updates/reconnects, assigned-rider location access, driver location acknowledgements/HTTP fallback, and guarded trip progression.
- Verification: 113 backend tests passed; React build and pip check passed; no schema drift; real TCP WebSocket/Redis integration tests passed; Vite upgrade forwarding and cross-process live delivery passed.
- Security checks: strict Origin/account/role/session boundaries, private channel isolation, location ownership/freshness, validation and update spacing, and logout/JWT-expiry closure on existing sockets passed.
- Failure checks: Redis outage preserves committed HTTP writes, reconnect rereads durable state, and old sockets/tasks/subscriptions are cleaned up. Pending visual/manual UI checks are explicitly unverified; the user has not tried the live badge yet.
- Source review: actual local credentials absent from all 28 changed/new files; ignored configuration/dependencies/build output remain untracked; whitespace check passed.
- Implementation commit: `4a99f39759ec485565597b570a02b6866006530d`.
- Remote: `https://github.com/rarjun07/Cab-Booking-Platform-Python-Stack.git`, branch `main`.
- Push result: succeeded; exact remote implementation SHA verified. This completion record follows in a documentation commit; compare current HEAD with the remote for the latest checkpoint.
- Known limits: manual coordinate sharing rather than device GPS, ephemeral Pub/Sub with snapshot recovery, demo driver verification policy, general rate/connection limits scheduled for Day 12, existing TestClient deprecation warning, no payments/final billing yet.
- Ready for next milestone: after this documentation checkpoint is pushed and verified, await the user's next instruction. Carry manual UI follow-ups forward explicitly.

Day 4:

- Scope delivered: driver-owned vehicle profiles, fresh online/offline location, indexed nearby queries, driver accept/decline dashboard, transactional assignment, and rider/driver open-ride recovery.
- Verification: 91 backend tests passed; React build and pip check passed; migration applied with no drift; legacy-data preservation and real concurrent acceptance tests passed; live local two-account API demo passed.
- UI follow-up: automated visual verification remains blocked by the earlier browser URL policy; user has not yet tried the manual driver-dashboard check. No browser pass is claimed.
- Source review: actual local credentials absent from all 23 changed/new files; ignored configuration/dependencies/build output remain untracked; whitespace check passed.
- Implementation commit: `834ae6e413fadb6a5e1c61a2c66d0d19191fe5b9`.
- Remote: `https://github.com/rarjun07/Cab-Booking-Platform-Python-Stack.git`, branch `main`.
- Push result: succeeded; exact remote implementation SHA verified. This completion record follows in a documentation commit; compare current HEAD with the remote for the latest checkpoint.
- Known limits: unverified demo profiles permitted and labeled; manual refresh/location renewal; geographic proximity rather than road ETA; accepted rides remain active until later trip-progression work; existing TestClient deprecation warning.
- Ready for next milestone: after this documentation checkpoint is pushed and verified, await the user's next instruction and resolve optional Day 5. Carry manual UI follow-ups forward explicitly.

Day 3:

- Scope delivered: OSRM road routing, configurable sample INR fares, signed rider-bound quotes, persistent ride requests, duplicate protection, owned status access, and the React booking form.
- Verification: 71 backend tests passed; frontend build and dependency check passed; migration applied with no schema drift; real OSRM/API estimate-create-retry-status-logout flow passed.
- UI follow-up: visual/manual verification remains pending because browser URL policy blocked the automated preview reload and the user has not yet tried the form. This is not a claimed browser pass.
- Source review: local credentials absent from all 24 changed/new files; local configuration and generated files remain ignored; whitespace check passed.
- Implementation commit: `ef48c41770db6eedb4392f350176f9fb379049ec`.
- Remote: `https://github.com/rarjun07/Cab-Booking-Platform-Python-Stack.git`, branch `main`.
- Push result: succeeded; exact remote implementation SHA verified. This completion record follows in a documentation commit; compare current HEAD with the remote for the latest checkpoint.
- Known limits: public OSRM service is best-effort; no live traffic; process-local throttling only; sample pricing; driver matching is not implemented. Existing TestClient deprecation warning remains.
- Ready for next milestone: after this documentation checkpoint is pushed and verified, await the user's next instruction and resolve optional Day 4 scope. Carry the manual UI check forward explicitly.

Day 2:

- Scope delivered: PostGIS core for the existing PostgreSQL 14 server; driver/ride/payment/review models; user profile fields; spatial indexes; Alembic baseline adoption and booking-schema migration.
- Verification: 43 backend tests passed; final 5 targeted migration tests passed; no schema drift; clean database status output; dependency consistency check passed.
- Data preservation: existing development user and session records compared equal before and after migration.
- Source review: actual local credentials absent from all 19 changed/new candidate files; ignored local configuration remains untracked.
- Implementation commit: `4ae8200b1345a202c18a4ab4ea2296f3e9a82030`.
- Remote: `https://github.com/rarjun07/Cab-Booking-Platform-Python-Stack.git`, branch `main`.
- Push result: succeeded; exact remote implementation SHA verified.
- Known environment detail: PostGIS was manually compiled for PostgreSQL 14 and must be rebuilt if that major installation changes. Existing TestClient deprecation warning remains documented.
- Ready for Day 3: yes, once this completion-record commit is also pushed and verified. No Day 3 feature work is included.

Day 1:

- Scope delivered: Git monorepo; FastAPI; React/Vite; local PostgreSQL development/test databases; real registration, login, protected sessions, and logout.
- Automated verification: 24 PostgreSQL-backed tests passed; frontend production build passed; dependency consistency check passed.
- Browser verification: API connectivity, signup, login, bad-password rejection, session verification, reload restoration, and sign-out passed.
- Source review: generated local credentials and signing secret are absent from tracked candidates; `.env`, installed dependencies, and build output are ignored.
- Known limits: no email verification, password reset, or refresh-token flow yet; session lifetime is 30 minutes. Login throttling is scheduled for Day 12. The test suite emits one HTTPX compatibility deprecation warning.
- Application commit: `dcf934062abca7bab47464104d13ca2b7a94bb45`.
- Remote: `https://github.com/rarjun07/Cab-Booking-Platform-Python-Stack.git`, branch `main`.
- Push result: succeeded; remote application SHA verified with `git ls-remote`.
- Ready for Day 2: yes, after the completion-record commit is also pushed and verified. No Day 2 implementation is included.

For each day, record the following using observed results. Do not mark a day complete on the strength of a plan or scaffold.

```text
Day:
Scope delivered:
Verification commands / manual checks:
Verification results:
Known issues or required configuration:
Commit SHA:
Remote URL and branch:
Push result and remote verification:
Ready for next day: yes / no
```

## Daily Git rule

Implementation -> relevant checks -> review -> commit -> push -> verify remote commit -> next day.

If the push fails or GitHub authentication is missing, keep the current day open and resolve that checkpoint. Never start the next day's implementation while the previous day's push is unverified.
