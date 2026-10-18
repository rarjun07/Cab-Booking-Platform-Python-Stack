# Day 2: PostgreSQL, PostGIS, and migrations

Day 1 introduced accounts and sessions for the user's choice of custom authentication. Day 2 extended that database with the mentor guide's booking models. This page also tracks later schema revisions; the feature walkthroughs explain the Day 3 booking and Day 4 matching APIs.

## Understand the tables

| Table | What it stores | Main relationship |
| --- | --- | --- |
| `users` | Name, email, password hash, role, optional phone/profile picture, average rating, wallet balance, and creation time. | The identity shared by riders and drivers. |
| `auth_sessions` | Session ID, user ID, expiry, and revocation time. | Each session belongs to a user. |
| `drivers` | Vehicle JSON, verification flag, current location, and active/offline status. | Its primary key is also a foreign key to `users.id`. |
| `rides` | Rider, optional assigned driver, pickup/drop points, status, fares, distance, duration, and creation time. | Rider references `users`; assigned driver references `drivers`. |
| `payments` | Ride, optional Stripe PaymentIntent ID, amount, and payment status. | One payment record per ride; Stripe IDs are unique when present. |
| `reviews` | Ride, reviewer, reviewed user, rating, and optional comment. | One review per reviewer per ride. |
| `ride_declines` (Day 4) | Driver decisions to decline specific requests. | Composite ride/driver primary key; both reference their existing records. |
| `payment_events` (Day 6, extended Day 10) | Processed signed Stripe event IDs, types, and timestamps. | Exactly one ride payment or wallet top-up; one global primary key prevents cross-kind event replay. |
| `receipt_emails` (Day 8) | Requesting account, private recipient/snapshot, document fingerprint, attempts and delivery status. | References ride/user; unique document per account/ride prevents duplicate jobs. |
| `promo_codes` (Day 10) | Percentage, cap, minimum fare, active dates and usage limits. | Unique normalized code, redeemed by riders. |
| `promo_redemptions` (Day 10) | Saved code and before/discount/final amounts. | One per ride; references code, ride and rider. |
| `wallet_topups` (Day 10) | Amount, owner, request UUID, provider reference, status and credit time. | Unique retry key per user; unique provider reference. |
| `wallet_entries` (Day 10) | Positive verified credits. | One entry per top-up, owned by its rider. |

The database protects basic integrity: referenced records must exist, fares/distances/durations cannot be negative, ratings must be 1-5, reviewers cannot rate themselves, and pickup/drop/driver coordinates must be in range.

Individual amounts use PostgreSQL `NUMERIC(10, 2)` and Python `Decimal`, preserving two decimal places without floating-point rounding. The cumulative wallet balance uses `NUMERIC(14, 2)` and starts at zero; webhook credits update it and the uniquely linked ledger atomically. See [PROMOS_WALLET.md](PROMOS_WALLET.md). `rating_avg` starts at zero; Day 9 maintains it atomically with review submissions while summary reads compute average/count from one query. See [REVIEWS.md](REVIEWS.md).

Cross-record business rules remain the responsibility of the later APIs: driver profiles require driver-role users, ride requests require riders, and reviews require completed rides and the actual ride participants. Model constraints do not claim to implement those flows.

## Understand PostGIS

PostGIS adds geographic types and operations to PostgreSQL. Our location columns are `geometry(Point, 4326)`, using longitude/latitude coordinates in the WGS84 coordinate system.

The order is **longitude first, latitude second**:

```text
POINT(77.2090 28.6139)
      longitude latitude
```

GiST spatial indexes exist on the driver's current location and both ride points. The tests verify the indexes and a real `ST_DistanceSphere` calculation in meters. Day 4 adds nearby matching and expression indexes on location/pickup cast to geography, so its radius uses meters. See [the matching walkthrough](RIDE_MATCHING.md).

## Understand migrations

A model describes the desired table structure in Python. An Alembic migration records a versioned change to the actual database. Changing a model alone does not update an existing database.

We now have eight revisions:

1. `0001_auth_baseline`: on a fresh database, creates the frozen Day 1 user/session schema. On an existing Day 1 database, checks its columns, indexes, foreign keys, primary keys, and role constraint before adopting it. It refuses unexpected unversioned tables or schema drift rather than silently stamping them as correct.
2. `0002_booking_models`: requires an administrator-enabled PostGIS extension, adds user profile fields/defaults, and creates the driver, ride, payment, and review tables and indexes.
3. `0003_ride_quote` (Day 3): adds nullable, unique `rides.quote_id` to prevent duplicate ride creation when a signed estimate is retried. Existing rides can retain a null quote ID.
4. `0004_driver_matching` (Day 4): adds nullable driver location timestamps, geography expression indexes, a partial unique active-driver assignment index, and the `ride_declines` table. Legacy locations are ineligible for matching until refreshed. Existing duplicate active assignments must be reconciled before this migration can create its unique index.
5. `0005_test_payments` (Day 6): adds payment INR currency, creation/paid timestamps, and a payment-event audit table. Existing payment amounts, status, and provider references are preserved; old `paid_at` values remain null rather than inventing payment times.
6. `0006_receipt_emails` (Day 8): adds versioned receipt-email requests with private server-owned snapshots, bounded delivery attempts, status/timestamps, and ride/user indexes. Existing rides and invoices are unchanged.
7. `0007_review_timestamps` (Day 9): adds a nullable review creation timestamp with a default for future inserts, preserving unknown legacy dates. Reconciles only the derived user rating average from existing reviews; account identity fields and feedback are preserved.
8. `0008_promos_wallet` (Day 10): adds a zero-default wallet balance, promo rules/redemptions, durable top-ups and unique credit entries. Extends the global event audit with an exactly-one-target constraint; existing ride events are preserved. Its downgrade deletes Day 10 tables/balance and wallet-targeted audit rows, retaining ride events.

Existing account fields, password hashes, IDs, and session records are retained. Added non-null user fields receive database defaults. Migrations import frozen schema definitions rather than future ORM models, so the historical steps remain stable.

The compatibility command `python -m scripts.init_auth_db` now runs Alembic migrations. Application startup does not change the schema, and tests use migrations instead of `create_all`.

## Commands to try on this machine

From your backend terminal:

```bash
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/backend"
source .venv/bin/activate
python -m alembic current
python -m alembic check
python -m scripts.db_status
```

Expected current revision: `0008_promos_wallet (head)`.

`alembic check` should report **No new upgrade operations detected**. `db_status` prints the installed PostGIS version and table/column names, without showing credentials or account data.

For a future reviewed schema change, use `python -m alembic revision --autogenerate -m "describe the change"`, review the generated file, then `python -m alembic upgrade head`. GeoAlchemy helpers exclude PostGIS system tables and handle spatial imports/indexes. Alembic does not automatically detect every kind of change (including all check-constraint changes); migrations still require review.

Downgrading removes columns/tables introduced by a revision. Our downgrade tests run only in the separate test database inside a transaction that is rolled back; we did not downgrade the development database.

## Set up a fresh database

1. Install a PostgreSQL server and a compatible PostGIS package/build.
2. Install the backend's `requirements.txt` in its virtual environment.
3. Configure ignored `backend/.env`. The existing `scripts.setup_local` can create our dedicated local role/databases when starting on a new Mac; it refuses to overwrite existing project resources.
4. Enable PostGIS once in each project database using a PostgreSQL administrator. On this machine the administrator is `arjunsair`:

```bash
psql -h 127.0.0.1 -U arjunsair -d cab_booking_dev -c 'CREATE EXTENSION IF NOT EXISTS postgis;'
psql -h 127.0.0.1 -U arjunsair -d cab_booking_test -c 'CREATE EXTENSION IF NOT EXISTS postgis;'
```

5. As the application, from `backend/`, run:

```bash
python -m alembic upgrade head
python -m scripts.db_status
```

The application role remains non-superuser and cannot create databases or roles. The extension is administrator-managed and is not removed by migration downgrades.

## PostgreSQL 14 installation notes for this Mac

The active service is PostgreSQL 14.21, used by other local projects as well. Homebrew's current PostGIS formula targets PostgreSQL 17/18. We retained the running server and built PostGIS 3.6.4 core for PostgreSQL 14.

- Installed Homebrew build dependencies: GEOS, PROJ, libxml2, pkgconf, and their required dependencies.
- Restored the missing PostgreSQL 14 header symlink at `/opt/homebrew/include/postgresql@14`, pointing to that version's existing Cellar headers. Main PostgreSQL command links and services were not changed.
- Downloaded the official source from `https://download.osgeo.org/postgis/source/postgis-3.6.4.tar.gz` and verified SHA-256 `ed8dc6679f1e06f7b113592b04cde2a7e00f1b1e681294c8ca2204058990cec6` against the Homebrew recipe before extracting it.
- Configured the core build with these options:

```bash
./configure --prefix=/private/tmp/cab-postgis-install \
  --with-pgconfig=/opt/homebrew/opt/postgresql@14/bin/pg_config \
  --with-geosconfig=/opt/homebrew/opt/geos/bin/geos-config \
  --with-projdir=/opt/homebrew/opt/proj \
  --with-xml2config=/opt/homebrew/opt/libxml2/bin/xml2-config \
  --with-jsondir=/opt/homebrew/opt/json-c \
  --without-raster --without-topology --without-protobuf \
  --without-sfcgal --without-address-standardizer
make -j1 PG_SYSROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk
make -C postgis install PG_SYSROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk
make -C extensions/postgis install PG_SYSROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk
```

Use a sequential build: parallel SQL generation encountered a raster upgrade-script race even with the raster library disabled. Regenerating SQL with `make -C raster/rt_pg -B sql_objs` and rerunning `make -j1` resolved it; only the core library and core extension were installed.

The resulting core library is `/opt/homebrew/lib/postgresql@14/postgis-3.so`, and the control/SQL files are in `/opt/homebrew/share/postgresql@14/extension`. Raster, topology, SFCGAL, and address-standardizer libraries are not installed and are not needed for this project's point/distance queries. This manual extension build must be rebuilt if that PostgreSQL major installation changes. No PostgreSQL restart was needed.

## Verification

Run `python -m pytest -q` from `backend/` after installing `requirements-dev.txt`.

Tests require the separate `_test` database and use rollback transactions. They cover authentication regressions, schema constraints, exact decimal fares, stored geographic points, spatial indexes/distance calculations, fresh migrations, upgrade/downgrade behavior, existing-account preservation, and refusal to adopt a modified unversioned baseline. Fresh migration SQL can also be rendered without connecting using `python -m alembic upgrade head --sql`.

No ride request, payment, review, or matching endpoint was added on Day 2. The schema prepares for those later milestones.

References: [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html), [GeoAlchemy migration helpers](https://geoalchemy-2.readthedocs.io/en/latest/alembic.html), [PostGIS installation](https://postgis.net/docs/postgis_installation.html), and [Homebrew's PostGIS recipe](https://github.com/Homebrew/homebrew-core/blob/HEAD/Formula/p/postgis.rb).
