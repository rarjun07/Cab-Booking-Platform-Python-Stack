# Day 3: fare estimates and ride requests

The goal is to turn two locations into a road-route estimate, then save an authenticated rider's request in PostgreSQL. The user chose a free alternative to the guide's Google Maps service, so this milestone uses OSRM routing with OpenStreetMap data. No maps API key is required for the default public demo.

## Try it step by step

1. Apply the database migration from `backend/` with the virtual environment active: `python -m alembic upgrade head`.
2. Keep FastAPI running with `python -m uvicorn app.main:app --reload --no-proxy-headers`.
3. In a separate terminal, run `npm run dev` from `frontend/` and open <http://127.0.0.1:5173/>.
4. Sign up or sign in with a **rider** account. Driver accounts cannot request rides.
5. Click **Use Delhi sample**. It fills pickup `28.6139,77.2090` and destination `28.6129,77.2295`; it does not send a routing request yet.
6. Click **Get fare estimate**. Review the distance, driving time, fare breakdown, and expiry.
7. Click **Request this ride** before the estimate expires. The page should show the saved ride reference and status `requested`.
8. Click **Refresh ride status** to read that ride from the API.

The original Day 3 form used coordinates. The later [map follow-up](FEATURE_COMPLETION.md) adds Leaflet selection and OSRM route previews in both dashboards. Latitude comes first in the form and API query; OSRM and PostGIS use longitude first internally. Coordinates go to the public routing service for estimates and saved-route previews. Viewed map areas also go to the tile provider. Attribution and a map-issue link remain visible.

Editing the locations clears the previous estimate. Changing accounts clears the booking state. Quotes expire after five minutes by default. If saving fails because of a network interruption, retrying the same valid quote returns the same ride instead of creating a duplicate.

This milestone saves ride requests. Driver assignment, availability, trip progression, and payments belong to later milestones.

## How the estimate works

FastAPI validates the coordinates and requests an OSRM driving route. It rounds distance up to whole meters and duration up to whole seconds, then calculates money using `Decimal` and rounds each charge to two decimal places:

```text
distance charge = distance in km × ₹12.00
time charge     = duration in minutes × ₹1.00
subtotal        = ₹50.00 base + distance charge + time charge
estimate        = max(₹80.00 minimum, subtotal)
```

These are illustrative project rates, not a real operator's prices. OSRM travel time does not include live traffic. The observed Delhi route returned 3,982 meters and 396 seconds: ₹50.00 + ₹47.78 + ₹6.60 = **₹104.38**. Routing results can change as road data changes.

The response includes a signed quote containing the rider ID, quote ID, locations, route metrics, price, and expiry. The client submits only that quote when requesting a ride. FastAPI checks its signature, audience, expiry, and rider before saving the server-issued values. A client-supplied fare or rider ID is not accepted.

Migration `0003_ride_quote` adds a unique quote ID to each new ride. This makes retries safe, including competing inserts. Existing rides remain valid with a null quote ID.

## API endpoints

All endpoints require a valid rider session cookie. The POST also requires an allowed `Origin` header, checked by the existing authentication protection.

| Method and path | Purpose |
| --- | --- |
| `GET /api/rides/estimate?origin=28.6139,77.2090&dest=28.6129,77.2295` | Returns route metrics, INR fare, breakdown, signed quote, and expiry. |
| `POST /api/rides/request` with JSON `{"quote_token":"<estimate quote>"}` | Saves a new ride (201), or returns the existing ride for the same valid quote (200). |
| `GET /api/rides/{ride_id}/status` | Returns the requesting rider's ride; another rider receives 404. |

Missing sessions return 401; driver accounts return 403. Invalid coordinates, identical points, missing routes, and invalid/expired quotes produce explanatory errors. The API returns 429 when uncached route requests arrive too quickly, 503 for routing unavailability, and 502 for malformed routing responses. It does not silently replace a failed road route with a straight-line estimate.

## Configuration and routing limits

Safe defaults are in `backend/.env.example`. Existing local environments use the same defaults without adding a key:

| Variable | Default | Meaning |
| --- | --- | --- |
| `OSRM_BASE_URL` | `https://router.project-osrm.org` | OSRM-compatible routing server. |
| `QUOTE_LIFETIME_SECONDS` | `300` | Quote validity period. |
| `FARE_BASE` | `50.00` | Sample base charge in INR. |
| `FARE_PER_KM` | `12.00` | Sample charge per kilometer. |
| `FARE_PER_MINUTE` | `1.00` | Sample charge per minute. |
| `FARE_MINIMUM` | `80.00` | Sample minimum fare. |

Restart FastAPI after changing configuration. The provider identifies this project in its User-Agent, allows at most one new upstream request per second per process, caches up to 256 routes for 60 seconds, and times out after 10 seconds. A route must snap to a road within 250 meters of each supplied point.

The public service is best-effort infrastructure for learning; availability and capacity are not guaranteed. Its operator can log routing queries. Before deployment, choose a suitable hosted provider or self-host OSRM, review its current usage/privacy policy, and use shared limits if running multiple application workers. This process-local throttle does not coordinate multiple workers or installations.

References: [OSRM HTTP API](https://github.com/Project-OSRM/osrm-backend/blob/master/docs/http.md), [demo-server usage policy](https://github.com/Project-OSRM/osrm-backend/wiki/Api-usage-policy), [linked routing-service policy](https://routing.openstreetmap.de/about.html), and [OpenStreetMap attribution](https://www.openstreetmap.org/copyright).

## Understand the files

| File | Responsibility |
| --- | --- |
| `backend/app/routing.py` | Calls OSRM, bounds requests, caches results, and translates service errors. |
| `backend/app/ride_schemas.py` | Validates coordinates, quote contents, and public request/response data. |
| `backend/app/rides.py` | Calculates fares, signs/checks quotes, saves rides, and restricts status access. |
| `backend/alembic/versions/0003_ride_quote.py` | Adds the unique nullable quote ID without removing existing rides. |
| `frontend/src/RideBooking.jsx` | Manages location inputs, quote expiry, booking, and status refresh. |
| `backend/tests/test_routing.py` | Checks provider behavior with controlled responses and no external network. |
| `backend/tests/test_rides.py` | Checks fare math, authorization, validation, quote security, and database persistence. |

## Verification evidence and pending UI check

- `python -m alembic upgrade head` applied `0003_ride_quote`; `python -m alembic check` found no model/schema drift.
- `python -m pytest -q`: **71 passed** against the separate PostgreSQL test database. The previously documented TestClient/HTTPX deprecation warning remains.
- `python -m pip check`: no broken requirements.
- `npm run build`: passed after the React changes.
- Live API check against the running development server: registered a synthetic rider, fetched a real OSRM route, saved a ride with 201, retried with 200 and the same ride ID, read owned status with 200, logged out, and received 401 on a subsequent status request. Synthetic user/ride records remain local development test data.
- Browser visual check: **unverified**. The browser URL policy rejected the automated preview reload. The user reported that they have not yet tried the manual form flow above. A successful build and API check do not establish visual behavior; carry this follow-up into the manual flow/UI testing milestones.

The evidence above records Day 3. Day 4 now extends this flow with [nearby matching and open-ride recovery](RIDE_MATCHING.md). Current verification and daily Git checkpoints are recorded in `PROGRESS.md`.
