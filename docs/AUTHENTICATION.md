# Day 1: FastAPI + PostgreSQL authentication

The user chose custom authentication instead of the mentor guide's Clerk/Supabase Auth options. The database connection and the `users` / `auth_sessions` tables therefore move into Day 1. PostGIS, the remaining application models, and Alembic migrations stay on Day 2.

Day 2 update: [the database walkthrough](DATABASE.md) now covers PostGIS and Alembic. The old `scripts.init_auth_db` command delegates to migrations and requires PostGIS to have been enabled by an administrator. Follow the updated database setup when installing on another machine.

## Understand the flow

1. React sends the sign-up form to FastAPI over our local Vite proxy.
2. FastAPI validates the name, email, password, and rider/driver role. Email addresses are normalized to lowercase.
3. Argon2 hashes the password with a random salt. PostgreSQL stores that hash, never the submitted password.
4. FastAPI creates a session record and signs a JWT containing the user ID, session ID, issue time, expiry, issuer, and audience.
5. The browser stores that JWT in an HTTP-only cookie. React does not read it or store a token in localStorage.
6. When React asks for `/api/auth/me`, the browser sends the cookie. FastAPI verifies the signature and claims and checks the corresponding PostgreSQL session.
7. Logout marks the session revoked in PostgreSQL and clears the cookie. Replaying that token is rejected.

Registration signs in the new user immediately. A page reload restores the session by checking the backend, rather than trusting browser state. Sessions expire after 30 minutes; there is no refresh-token flow in this Day 1 scope. Sign in again after expiry.

Driver sign-up selects a role only; vehicle verification and driver availability belong to the later driver milestone. Selecting driver does not imply a verified driver profile.

## Run the project

The current machine has dedicated databases `cab_booking_dev` and `cab_booking_test`, owned by `cab_booking_app`. Local credentials and a randomly generated signing secret are in ignored `backend/.env` with owner-only file permissions. They are not committed or printed in setup output.

Keep these two terminals running:

```bash
# Terminal 1
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/backend"
source .venv/bin/activate
python -m uvicorn app.main:app --reload --no-proxy-headers
```

```bash
# Terminal 2
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/frontend"
npm run dev
```

Open <http://127.0.0.1:5173>. Use the same hostname throughout the test because cookies are tied to a hostname. Reuse a server that is already running on its expected port.

### Try the authentication flow

1. Under **Create account**, enter a name, email, password of 12-128 characters, and a rider/driver role.
2. Submit the form. Your name should appear after the database stores the account.
3. Click **Verify my session**. FastAPI should confirm the session.
4. Reload the page; you should still be signed in until session expiry.
5. Click **Sign out**, then use **Sign in** with the same credentials.
6. An incorrect password should show a generic error. An existing email cannot be registered twice.

Day 1 does not send verification emails or implement password recovery. Those are follow-up authentication features rather than claims of production readiness. Redis-backed login throttling remains scheduled for Day 12; public deployment remains Day 14.

## Endpoint reference

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | API availability check; no database health claim. |
| POST | `/api/auth/register` | Validate and create a PostgreSQL account; set its session cookie. |
| POST | `/api/auth/login` | Verify email/password and create a session. |
| GET | `/api/auth/me` | Return the authenticated user's public fields. |
| POST | `/api/auth/session` | Verify the current session, corresponding to the guide's session endpoint. |
| POST | `/api/auth/logout` | Revoke the session and clear its cookie. |

Authentication POST requests require an allowed `Origin` header. The React browser supplies it automatically. Swagger UI supplies its own allowed local origin. For terminal clients, supply `Origin: http://127.0.0.1:5173` and use a cookie jar; a bearer Authorization header alone is not this implementation's authentication transport.

Only `id`, `name`, `email`, and `role` are returned. Passwords, hashes, database credentials, and JWTs are excluded from JSON responses. Validation errors omit echoed input values so invalid passwords are not reflected back.

## Understand the backend files

| File | Responsibility |
| --- | --- |
| `app/config.py` | Read typed settings from environment variables / `backend/.env`. |
| `app/database.py` | Connect to PostgreSQL and provide a database session per request. |
| `app/models.py` | Define the two authentication tables with SQLAlchemy. |
| `app/schemas.py` | Validate forms and define safe user responses. |
| `app/auth.py` | Hash/verify passwords, issue/check tokens, check request origins, and revoke sessions. |
| `app/main.py` | Register routes, retain the health endpoint, and redact validation inputs. |
| `scripts/setup_local.py` | One-time local project role/database creation with ignored generated configuration. |
| `scripts/init_auth_db.py` | Explicitly create Day 1 tables; no automatic startup schema changes. |
| `tests/` | Real PostgreSQL authentication checks with per-test rollback. |

`frontend/src/AuthPanel.jsx` contains the account forms and session restoration. The existing health-check page is retained.

## Setup on a different Mac

Install and start PostgreSQL first. Install backend dependencies using `python -m pip install -r requirements.txt` inside the Python virtual environment.

If the local PostgreSQL server accepts an administrative connection for the current macOS username at `127.0.0.1`, run from `backend/`:

```bash
python -m scripts.setup_local
python -m scripts.init_auth_db
```

Setup refuses to overwrite an existing `.env`, role, or project database. If setup is interrupted, retain the generated `.env` and inspect the project role/databases before retrying; it deliberately does not reset passwords or delete databases.

For a password-protected or hosted PostgreSQL server, configure the role/databases yourself and copy `.env.example` to `.env`. Set its two database URLs and generate your own long random `JWT_SECRET`. Then run `python -m scripts.init_auth_db`. Database URLs use SQLAlchemy's `postgresql+psycopg://` format.

`COOKIE_SECURE=false` is only for local HTTP. Its code default is `true`; use HTTPS and secure cookies for deployment. Configure `ALLOWED_ORIGINS` as a JSON array of exact approved frontend origins when deploying. The Vite proxy is development-only.

## Run meaningful tests

From `backend/`, with the virtual environment active:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Tests require `TEST_DATABASE_URL` for a separate PostgreSQL database whose name ends in `_test`. They refuse the development database and roll back each test's records. Since Day 2, they initialize tables using Alembic; migration downgrade checks also run inside rollback transactions in that test database. They do not delete databases or truncate development tables.

Checks cover password hashes, cookie attributes, duplicate/case-insensitive emails, invalid inputs, incorrect credentials, missing/tampered/expired tokens, invalid token claims, missing database sessions, origin checks, and logout revocation.

The current Starlette version emits a deprecation warning about its HTTPX TestClient compatibility path. The tests pass using the installed HTTPX version; this is a test dependency warning, not an authentication failure.

References: [FastAPI password hashing and JWT tutorial](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) and [SQLAlchemy PostgreSQL driver documentation](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg).

## Day 5 WebSocket authentication

Live endpoints are under `/api/ws/`, so the browser sends the existing HTTP-only cookie scoped to `/api`. The server checks the exact Origin, JWT, database session, account ID, and role before accepting. Each broker event and incoming message triggers another session check; idle connections are rechecked every two seconds by default. Expired or revoked accepted connections close with code `4401`. Credentials are never placed in the socket URL or browser storage. See [the realtime walkthrough](LIVE_UPDATES.md) for the tested protocol and privacy boundaries.
