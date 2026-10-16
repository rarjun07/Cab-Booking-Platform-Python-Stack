# Day 4: driver dashboard and nearby matching

The user chose to include this optional milestone. A driver can save vehicle details, provide a location, go online/offline, see nearby requests, and accept or decline. A rider can find nearby available drivers and refresh the saved ride to see an assignment.

This is a learning demo. Driver profiles start unverified, and matching currently allows those profiles. The dashboard and rider candidate list label that state. Saving a vehicle does not verify it; the API rejects a submitted `verified` field and clears verification if vehicle details change. A real verification/approval process is needed before offering real rides.

## Start the applications

Keep FastAPI and React running in separate terminals. Reuse either server if it is already running.

Backend:

```bash
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/backend"
source .venv/bin/activate
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

Frontend:

```bash
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/frontend"
npm run dev
```

Open <http://127.0.0.1:5173/>. If the temporary preview has been stopped, run the frontend command again.

## Try the driver side first

1. Create an account with **I'm joining as a → Driver**, or sign in to an existing driver account.
2. In the driver dashboard, enter a make, model, and number plate. For a demo, you can use `Maruti`, `Dzire`, and `DL-DEMO-001`.
3. Click **Save vehicle profile**. Your new profile starts offline.
4. Click **Use Delhi sample location**. This fills latitude `28.6140` and longitude `77.2090` without requesting device GPS access.
5. Click **Go online**. The dashboard should show **Online** and a location expiry time.
6. Click **Refresh dashboard** to fetch nearby ride requests. An empty list is expected until a rider requests a ride near this location.

The location expires after five minutes by default. Click **Refresh location / go online** to submit a fresh location. A dashboard refresh only reads data; it does not extend location freshness. **Go offline** clears the matching location and stops new offers. An already accepted ride stays assigned.

## Request and match a ride

You can use one browser and switch accounts. For simultaneous views, use separate browser profiles or a normal and private window; tabs in the same profile share the login cookie.

1. Sign out of the driver account, then sign in as a rider. Signing out revokes that login session; it does not change the driver's explicitly saved availability. Use **Go offline** when you want to stop offers.
2. Choose **Use Delhi sample → Get fare estimate → Request this ride**. The sample driver is about 12 meters from this pickup.
3. Click **Find nearby drivers**. Eligible drivers appear in distance order. This list shows candidates; it does not assign one automatically.
4. Sign out and return to the driver account before its location expires. Click **Refresh dashboard**; refresh the location if needed.
5. Click **Accept ride** on the rider's request. The dashboard should display the accepted ride reference, pickup/destination, and estimated fare.
6. Sign back in as the rider. The latest open ride is restored automatically; **Refresh ride status** should show `accepted` and the assigned driver reference.

To try declining, create a separate request while an eligible driver has no active ride, then choose **Decline ride**. That request disappears for that driver and remains available to other eligible drivers. There is no undo-decline control in this milestone. Accepted drivers stay busy; trip progression/completion is a later step, so use a separate demo driver when testing another acceptance.

The rider restoration endpoint returns only the latest open request/ride, not a history list. Existing multiple open requests are retained in PostgreSQL and can still be accessed by their owner using their saved references. Ride history remains Day 8 work.

## How matching works

- The default matching radius is **5,000 meters** from the ride's pickup.
- A candidate must have a driver-role user, an online profile, a location updated within the last five minutes, no active ride, and no decline for this request.
- Riders see at most 10 candidates, ordered by distance. Drivers see at most 20 unassigned requests, ordered by pickup distance and then creation time/reference.
- PostGIS casts the stored WGS84 points to `geography`. `ST_DWithin` filters by radius and `ST_Distance` orders by geographic distance in meters. These are not road distances or traffic ETAs; Day 3 still uses OSRM for the rider's route and fare.
- Any eligible nearby driver can accept. Acceptance locks the driver row first, then the ride row, and rechecks availability, freshness, range, declines, and assignment.
- The first successful transaction assigns the driver and changes the ride to `accepted`. Competing acceptance attempts return 409. Retrying an acceptance already owned by that driver returns the same ride.
- A partial unique index prevents one driver from holding more than one `accepted`, `arriving`, or `in_progress` ride, even if another database writer bypasses the endpoint.

There is no automatic polling, WebSocket, Redis presence, device GPS tracking, or OSRM request for nearby matching. Users refresh explicitly; Day 5 realtime remains optional and undecided.

## API endpoints

Driver endpoints require a valid **driver** session. Rider endpoints require a valid **rider** session and restrict reads to the owning rider. Every PUT/POST also requires an allowed Origin.

| Method and path | Purpose |
| --- | --- |
| `GET /api/drivers/me` | Read the current driver's profile; returns null before setup. |
| `PUT /api/drivers/me` | Save `{"vehicle_info":{"make":"Maruti","model":"Dzire","plate":"DL-DEMO-001"}}`. Creates or updates only the signed-in driver's profile. |
| `POST /api/drivers/me/availability` | Go online with `{"status":"active","location":{"latitude":28.614,"longitude":77.209}}`, or offline with `{"status":"offline"}`. |
| `GET /api/drivers/me/offers` | List nearby available requests; offline, stale, or busy drivers receive an empty list. |
| `POST /api/drivers/me/rides/{ride_id}/accept` | Accept an eligible request; returns the assigned ride. |
| `POST /api/drivers/me/rides/{ride_id}/decline` | Remember this driver's decline; returns 204. Repeating a decline is safe while the ride remains eligible. |
| `GET /api/drivers/me/ride` | Read this driver's active ride, or null. |
| `GET /api/rides/{ride_id}/drivers` | Read nearby candidates for the owning rider's unassigned request. Assigned requests return an empty list. |
| `GET /api/rides/current` | Restore the signed-in rider's latest open ride/request, or null. |

Unauthenticated calls return 401 and wrong-role calls return 403. Invalid inputs return 422; missing/unowned rides return 404; stale, busy, declined, out-of-range, or already assigned requests return 409. The matching responses omit account emails, password hashes, and exact driver coordinates; an offered ride includes the pickup/destination the driver needs to evaluate it.

## Schema and configuration

Migration `0004_driver_matching` adds:

- `drivers.location_updated_at`, nullable so existing locations start ineligible until explicitly refreshed.
- GiST expression indexes for `drivers.current_location::geography` and `rides.pickup_point::geography`, matching the meter-based queries.
- `uq_rides_active_driver`, the partial unique index for active assignments.
- `ride_declines`, keyed by ride and driver, with foreign keys and a creation timestamp.

It preserves existing users, profiles, ride quotes, fares, and points. If an imported database already contains multiple active rides for one driver, the unique-index migration refuses to proceed; reconcile those assignments before upgrading. Downgrades remove the added protections and decline records, so use them only for a reviewed rollback. Our migration tests downgrade only the dedicated test database inside rolled-back transactions.

Optional settings in `backend/.env.example`:

```dotenv
MATCHING_RADIUS_METERS=5000
DRIVER_LOCATION_MAX_AGE_SECONDS=300
```

Defaults work with the existing local `.env`; no new account, key, or dependency is required. Restart FastAPI after changing settings.

## Understand the files

| File | Responsibility |
| --- | --- |
| `backend/app/driver_schemas.py` | Validates vehicle details and availability; defines minimal public matching data. |
| `backend/app/drivers.py` | Own-profile access, fresh availability, spatial queries, declines, and transactional acceptance. |
| `backend/app/rides.py` | Existing Day 3 flow plus rider-only restoration of the latest open ride. |
| `backend/alembic/versions/0004_driver_matching.py` | Versioned schema/index changes. |
| `frontend/src/DriverDashboard.jsx` | Vehicle form, location/availability controls, requests, and current assignment. |
| `frontend/src/RideBooking.jsx` | Rider estimates/requests plus nearby candidates and restored assignment. |
| `backend/tests/test_drivers.py` | Access rules, lifecycle, spatial filtering, declines, index protection, and real concurrent acceptance. |

## Verification and remaining manual check

- Final backend suite: **91 passed**. The previously documented TestClient/HTTPX deprecation warning remains.
- Migration applied to development; Alembic check reports no drift. Test migrations verify fresh upgrade/downgrade, auth preservation, and preservation of Day 3 driver points, quotes, and fares.
- Concurrent tests use separate PostgreSQL connections and committed synthetic fixtures in the guarded `_test` database. Both competing-drivers/one-ride and one-driver/two-rides scenarios produce exactly one winner, and fixtures are removed afterward.
- React production build passed; pip dependency check passed.
- Live local API demo passed: two synthetic accounts, vehicle setup, online availability, real OSRM estimate, ride creation, nearby driver at 12 meters, offer, acceptance, safe repeat acceptance, rider/driver restoration, offline location clearing without losing assignment, and logout revocation. The demo driver is left offline; synthetic accounts and the accepted ride remain development test data.
- React preview returned HTTP 200. Automated visual/browser interaction remains unverified because the earlier browser URL-policy rejection prevented preview automation. Manual feedback is tracked in `PROGRESS.md`; a successful build/API check is not a claimed browser pass.

References: [PostGIS meter-based radius queries](https://postgis.net/docs/ST_DWithin.html), [SQLAlchemy row locking](https://docs.sqlalchemy.org/en/20/core/selectable.html#sqlalchemy.sql.expression.GenerativeSelect.with_for_update), and [PostgreSQL partial indexes](https://www.postgresql.org/docs/14/indexes-partial.html).
