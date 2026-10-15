# Project progress

## Current checkpoint

- Active milestone: Day 1, final verification and Git checkpoint.
- Completed: read all nine PDF pages, checked the daily schedule, confirmed stack compatibility, and prepared the roadmap.
- Learning preference: guide the user step by step with explanations.
- Day 1 implementation: custom FastAPI + PostgreSQL authentication implemented and verified in the browser; final checks and commit/push checkpoint in progress.
- Git repository: initialized locally with branch `main`; no commits yet.
- GitHub account supplied by user: `rarjun07`.
- GitHub access: verified with `gh auth status`; `rarjun07` is the active account.
- Repository URL: https://github.com/rarjun07/Cab-Booking-Platform-Python-Stack (supplied by user).
- Remote: `origin` -> `https://github.com/rarjun07/Cab-Booking-Platform-Python-Stack.git` (fetch and push verified locally).
- Repository verification: `gh repo view` confirmed the intended owner/name and that the repository was empty before our first push.
- Last daily commit: none.
- Last verified push: none.
- Next action: finish the Day 1 review, commit and push, then verify the remote SHA. Do not start Day 2 yet.

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

## Daily completion record

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
