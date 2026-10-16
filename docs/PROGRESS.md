# Project progress

## Current checkpoint

- Active milestone: Day 3 implementation verified through automated and live API checks; commit/push checkpoint pending. Visual/manual UI follow-up remains unverified.
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
- Next action: complete and verify the Day 3 Git checkpoint. Day 4 has not started; its optional scope will be resolved when the user requests the next milestone.

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
- Day 3 commit/push is pending. Day 4 has not started.

## Daily completion record

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
