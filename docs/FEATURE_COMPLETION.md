# Mentor-guide follow-ups

On 2026-10-21 the user asked to build the remaining audited features one at a time, preserving the existing UI/palette and free-routing choice. These are explicit follow-ups to the existing days, not a claim that Day 14 is finished. Finish checks and a verified Git checkpoint for each implementation milestone before the next.

## Sequence

1. Interactive Leaflet maps in both dashboards, marker selection, OSRM road geometry and private saved-route access.
2. Driver pickup/destination ETA and visual tracking from fresh location updates; optional device location sharing with explicit browser consent.
3. Editable account details (existing name/phone/photo fields) and an operator-controlled driver-verification process. The guide does not require a new public admin dashboard.
4. Real Stripe sandbox ride-payment and wallet-top-up verification. Account/test keys must be configured locally, never pasted in chat or committed; this remains dependent on the user's account access.
5. External receipt-email setup and delivery verification. Provider/sender credentials and permission to send a specific verification message are required; local SMTP testing is not an external inbox pass.
6. Background cleanup/reconciliation and Redis presence follow-ups, with bounded/idempotent jobs and tests. These are backend tasks, not invented dashboard tabs.
7. Docker storage recovery and complete Compose smoke checks; select a hosting destination, then prepare a concrete deployment. Do not restart the other project's database, prune data or purchase services implicitly.
8. Manual rendered desktop/mobile/zoom/keyboard/screen-reader and configured-provider verification. Previous browser policy restrictions remain in effect. Keep unverified checks visible.

The PDF lists Tailwind, React Query/SWR and Redux/Recoil; current styling/fetch/state differs. This is a tooling-alignment decision separate from missing business features. React is the user's choice and Next.js is optional. Do not replace the working UI wholesale just to change libraries.

## 1. Maps

`JourneyMap.jsx` wraps Leaflet 1.9.4 for both roles. Riders select **Set pickup** or **Set destination**, then click the map; keyboard-accessible numeric fields remain available. Drivers can select a draft coordinate; clicking does not automatically go online or publish it. **S** is an unsent selection; **D** is a fresh server-confirmed driver location. Availability and **Share updated location** remain explicit actions.

Fare estimates now include a bounded GeoJSON LineString. Geometry is excluded from the signed fare token and is not used as client-supplied billing input. Restored rides load `/api/rides/{ride_id}/route`; only the owning rider or assigned driver can access this endpoint, checked before any upstream request. Existing Redis route quotas, OSRM throttling/cache/timeouts and safe errors apply. A route is a current road preview, not a persisted historical path or a live-traffic ETA. A failed route preview leaves trip controls usable; no fake straight-line road is drawn.

Map tiles use `https://tile.openstreetmap.org/{z}/{x}/{y}.png`, visible attribution, normal browser caching and an origin referrer. No tile prefetching/offline downloads are implemented. Viewed areas go to the tile provider; route coordinates go to OSRM when estimating or restoring a preview. Default Delhi view does not use device GPS. The public tile/routing services are best effort for learning; choose production-appropriate providers before public launch.

Optional public Vite build-time configuration: `VITE_MAP_TILE_URL` and `VITE_MAP_ATTRIBUTION` (trusted operator-controlled HTML attribution, never user input). Rebuild after changing them. These values are public; never put a secret API key in Vite variables. Changing the tile host also requires updating the on-screen provider disclosure.

Verification: backend authorization/geometry/cache tests, React coordinate conversion/selection/StrictMode cleanup tests, existing component/accessibility regressions, and production build. These do not establish actual browser tile rendering, mobile layout or screen-reader usability; those manual checks remain pending.

References: [Leaflet API](https://leafletjs.com/reference.html), [OSRM API](https://project-osrm.org/docs/v5.24.0/api/), [OSM tile policy](https://operations.osmfoundation.org/policies/tiles/).

## 2. ETA and device location

The map checkpoint `338347524ce02d5bd98019325860ae492757a3ab` was pushed and verified before this milestone started.

Both participants can read `/api/rides/{ride_id}/eta`. Before the trip starts it routes the driver's fresh server-confirmed position to pickup; during `in_progress` it routes to destination. Offline, expired, missing and unassigned locations yield no time; finished trips yield no ETA. An exact shared coordinate matching the stop returns zero without an upstream request. Invalid/missing road routes are errors, never invented driving times. Returned coordinates, timestamp, expiry and road geometry are private to participants. It does not change the trip fare.

React refreshes approximately every 15 seconds, waits until the previous request finishes, pauses while the browser document is hidden, aborts on trip changes/unmount, hides an expired ETA and stops on completion. The initial small delay avoids contention with the saved-route preview. A dashed line shows the current driver-to-stop road route. Estimates exclude live traffic and can lag actual movement.

Driver **Use my device location** requests browser permission and fills draft coordinates only. Go online/share still require explicit actions. After going online, **Start live GPS sharing** opts in to a browser watcher; successful updates go through the existing authenticated WebSocket with HTTP fallback when disconnected. Updates are limited to one per 15 seconds. Errors stop sharing. Stop/offline/logout/unmount clear the watcher; stopping alone leaves the last shared location until expiry, while Go offline clears it immediately. Device GPS requires localhost or HTTPS. Browser fixes, accuracy, permission dialogs and rendered tracking still need a real-device/manual check.

## 3. Account details and operator vehicle review

The ETA/GPS checkpoint `3d3b9d64f7acac2cf02fc5121246b3ba754d9889` was pushed and verified before this milestone began.

Open the profile dropdown, then **View profile**. Both roles can save a display name, optional international phone and optional HTTPS profile-picture URL. Blank phone/photo fields remove those values; image failures show initials. The backend selects the signed-in account, checks Origin and validates/normalizes inputs. IDs, roles, email, passwords, balances and verified flags cannot be changed through this form. Phone is contact data only, not phone verification or a login identifier. The backend never fetches the photo URL; the browser loads the saved image directly, without a referrer. This is URL-based pictures, not uploaded-file storage.

Alembic `0010_driver_verifications` adds a review log without changing existing accounts, sessions or vehicles. Operators with trusted terminal/database access can record a vehicle review, including the outcome, vehicle snapshot, OS account, reason and timestamp. Ordinary browser accounts cannot approve themselves. Review the actual vehicle/driver evidence separately: this command only records the operator's decision and performs no government/KYC check. Existing learning-demo matching still permits clearly labeled unverified profiles; recording this flag does not introduce production compliance or force active trips to end.

From `backend/` with the virtual environment active:

```bash
python -m alembic upgrade head
python -m app.verify_driver --driver-id '<driver UUID>' --status approved --plate '<reviewed number plate>' --reason 'Reviewed the current demo vehicle'
```

The second command is a dry-run. Confirm the correct driver/plate and review outcome, then add `--apply` to save it. Use `--status revoked` to withdraw approval. Do not include identity-document numbers or secrets in reasons. The command locks the driver row and checks the reviewed plate; if the vehicle changed, review again. A later vehicle edit automatically revokes approval and records that event. Re-saving identical details preserves approval. Decisions publish a normal live invalidation; a Redis outage does not roll back a saved review. This is a local operator workflow, not a new browser admin role or dashboard.

External Stripe/email setup, Docker recovery/hosting and actual rendered-browser/provider verification remain separate pending steps. Do not paste secrets into chat.
