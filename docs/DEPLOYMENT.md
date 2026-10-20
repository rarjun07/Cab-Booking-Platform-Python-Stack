# Day 14: Docker and deployment

## 1. Understand the files

`backend/Dockerfile` packages Python, the pinned application packages, Pango and
fonts for Linux PDF receipts. FastAPI, Alembic and Celery share this image, with
different startup commands. The app runs as a non-root user; API/worker root
filesystems are read-only, with temporary scratch space.

`frontend/Dockerfile` builds React with Node and copies the result into an
unprivileged nginx server. Node, npm and frontend development dependencies are
absent from the final web image. `.dockerignore` allowlists keep local `.env`
files, `.venv`, tests and `node_modules` out of build contexts.

`deploy/database/Dockerfile` adds PostGIS to the official multi-architecture
PostgreSQL 17 image, including Apple Silicon support. On a new volume, the
administrator creates `cab_booking`, enables PostGIS, and creates `cab_app`
without superuser/database/role creation privileges. Alembic then creates the
application schema as `cab_app`. Your native PostgreSQL 14 development data is
not copied or migrated by this setup.

`compose.yaml` waits for database/Redis readiness and a successful one-shot
Alembic migration before starting the app. A failed migration blocks API/worker
startup. Project-owned database/Redis volumes retain data. Redis AOF reduces
queue loss across restarts; application idempotency still matters.

Only nginx is published, at **127.0.0.1:8080**. PostgreSQL, Redis and FastAPI have
no host ports. Redis is unauthenticated on a private internal network for this
local setup; never publish it. React, HTTP API and WebSockets share one origin.
nginx replaces incoming forwarded IP/scheme headers; Uvicorn trusts only nginx's
fixed `172.30.87.2` address. If this subnet conflicts with a VPN/network, update
the edge subnet, nginx address and Uvicorn trust address together. Containers on
these private networks are trusted infrastructure.

## 2. Generate private local settings once

From the project root:

```bash
python3 scripts/setup_compose.py
docker compose config --quiet
```

The helper creates independent random passwords/JWT secret in `.env.database`
and `.env.compose`, ignored by Git with mode `0600`. It refuses to overwrite
either file and does not read/change `backend/.env`. Keep both files private and
back them up securely. They are plaintext configuration, not an encrypted secret
store; Docker administrators can read container environments. Avoid sharing full
`docker compose config`/inspect output. `config --quiet` validates without
printing values.

| Variable in `.env.compose` | Purpose |
| --- | --- |
| `DATABASE_URL` | Restricted `cab_app` on private service `database` |
| `JWT_SECRET` | Independent random signing key |
| `COOKIE_SECURE=false` | Loopback HTTP demo only |
| `ALLOWED_ORIGINS` | Exact localhost/127.0.0.1 origins on port 8080 |
| `REDIS_URL` | Private `redis` service, not host loopback |
| `RECEIPT_EMAIL_ENABLED=false` | No external mail delivery |
| `OSRM_BASE_URL` | Existing free learning demo |

Changing a password in an env file **does not change an existing SQL role**:
initialization runs only on an empty volume. Rotate the SQL role and app setting
together, after backup. Do not delete volumes to repair a password mismatch.

## 3. Build and start

Docker Desktop must be running with sufficient free host/VM storage:

```bash
docker compose up --build -d --wait --wait-timeout 180
docker compose ps --all
```

After startup passes, open [the Docker app](http://127.0.0.1:8080/) and register a
new demo account. This database is separate from the Vite/native app on port
5173. The first build downloads images/packages; it configures no paid hosting.

API readiness checks the migration head, PostGIS and Redis as well as HTTP.
`/api/health` alone is only API availability. Worker health checks infrastructure;
the smoke script separately checks that a real task is consumed. `migrate`
should show `Exited (0)`, because it is not a long-running server.

```bash
docker compose logs --tail 50 migrate backend worker
docker compose exec backend python -m alembic current
docker compose exec backend python -m alembic check
docker compose stop
docker compose start
```

Use `docker compose up -d --build --wait` after editing code/settings. `start`
resumes existing containers; it does not apply edited settings. `down` removes
this project's containers/networks and retains named volumes. **Do not add
`--volumes`/`-v` unless deliberately deleting data.** Avoid system-wide prune
commands or restarting Docker when another project's container is in use.

If Docker reports a read-only internal filesystem, stop retrying builds. Check
host/VM storage and resolve Docker's storage error. Restarting Desktop interrupts
all its containers; coordinate that action with the user first. Do not reset
Docker, prune other projects or delete volumes as an automatic workaround.

## 4. Verify the running containers

Configuration-generator safety tests can run without Docker:

```bash
python3 -m unittest discover -s tests -v
```

With the existing backend development virtual environment:

```bash
backend/.venv/bin/python scripts/smoke_compose.py --restart
```

The script uses actual HTTP through nginx, cookie-authenticated WebSockets,
PostgreSQL/PostGIS, Redis and Celery. It checks registration/login, Origin
rejection, logout/revocation, forwarded-IP spoofing against a Redis quota,
migration head, restricted SQL privileges, Linux PDF generation and a broker task.
`--restart` restarts only this Compose database/Redis and recreates its API,
then checks session persistence and nginx upstream recovery. Its generated
account/sessions are removed in `finally`. No passwords/cookies are printed;
there are no real routing/payment/email calls.

This consumes the one-minute registration quota. Wait at least 60 seconds before
rerunning it or registering another account from that client IP. It is a local
smoke check, not a production-site load test or a rendered browser check.

## 5. Back up before updating

Keep dumps private, in ignored `tmp/`, and copy them to secure backup storage:

```bash
mkdir -p tmp
docker compose exec -T database pg_dump -U postgres -d cab_booking -Fc > tmp/cab-booking.dump
```

Test restores into a separate database, never over the current database. Back up
configuration secrets separately. Dumps can contain private data and password
hashes; never commit them. Redis AOF does not replace SQL backups. For rollback,
stop the app, retain volumes, and assess schema compatibility before using an
older image. Do not automatically downgrade migrations or overwrite a database.

## 6. Online deployment needs a chosen target

No hosting destination/domain has been supplied; no online deployment is claimed.
This loopback configuration needs adaptation before internet use:

1. Confirm server/account, domain, region and cost with the user. Ensure Docker
   and persistent storage are supported; the PDF does not authorize purchases.
2. Configure HTTPS, `COOKIE_SECURE=true` and exact HTTPS origins. Adapt forwarded
   headers and Uvicorn trust to the actual TLS proxy chain, keeping app/data ports
   private. Verify rate limits through that edge. Do not simply expose port 8080.
3. Provision persistent PostgreSQL/PostGIS/backups and restricted credentials;
   use private authenticated/TLS Redis as appropriate. Run Alembic before the
   app. Review/scan images and pin tested digests for releases. Test restoration.
4. Select suitable hosted/self-hosted routing before public production use. The
   OSRM demo is a learning service with no availability guarantee.
5. If enabling email, configure a verified SMTP sender, credentials and STARTTLS.
   The worker currently has only the internal data network; grant outbound
   connectivity for the selected SMTP service explicitly. Container `localhost`
   is not your Mac's catcher. Remote plaintext SMTP remains prohibited.
6. Keep Stripe test-only and resume the deferred real-provider/webhook checks
   separately. Fixture-signed events do not verify the actual provider. Review
   demo driver eligibility/verification before accepting real rides.
7. Smoke-test the actual HTTPS URL: page/assets, cookies, origins, ownership,
   WebSockets/reconnect, routing, PDF, worker/mail, restart persistence and relevant
   sandbox payment/webhook flows. Finish pending browser/mobile/zoom/keyboard/
   screen-reader checks.

The guide includes a **deployed smoke check** in Day 14. Local container checks
and online verification must be recorded separately in the progress log.

## Primary references

- [Compose startup dependencies](https://docs.docker.com/compose/how-tos/startup-order/)
- [PostGIS image architecture](https://github.com/postgis/docker-postgis)
- [Official PostgreSQL image architectures](https://github.com/docker-library/official-images/blob/master/library/postgres)
- [nginx unprivileged image](https://github.com/nginx/docker-nginx-unprivileged)
- [Uvicorn proxy trust](https://uvicorn.dev/settings/)
- [WeasyPrint Linux/Pango requirements](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html)
