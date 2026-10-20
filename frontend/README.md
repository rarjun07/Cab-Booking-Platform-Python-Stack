# React frontend

The page now includes PostgreSQL-backed sign-up, sign-in, session restoration, verification, and sign-out. See [the authentication walkthrough](../docs/AUTHENTICATION.md).

Day 3 adds a coordinate form, public Delhi sample, fare breakdown, ride request, and status refresh for signed-in riders. See [the ride-booking walkthrough](../docs/RIDE_BOOKING.md) for a step-by-step demo. The production build passes; the new form's visual/manual browser check remains pending.

Day 4 adds the driver dashboard, vehicle setup, online/offline controls, location freshness, nearby offers, and accept/decline actions. Riders can find nearby drivers and recover their latest open ride after signing in. See [the matching walkthrough](../docs/RIDE_MATCHING.md) for the two-account demo and verification limits. Day 4 originally used explicit refresh buttons; Day 5 now adds realtime.

Day 5 adds live updates through `useRealtime`, an announced connection status, automatic reads of protected ride data after notifications, connection retries, location sharing, and trip-step buttons. Refresh controls remain as a fallback. See [the realtime walkthrough](../docs/LIVE_UPDATES.md); the new UI manual/visual check remains pending.

Day 6 adds `RidePayment` to completed rides. It lazy-loads Stripe.js, renders Stripe's Payment Element, confirms test payments, and displays only backend-verified payment success. Test keys belong in the backend's ignored `.env`; no frontend secret variables are required. Follow [the payment walkthrough](../docs/PAYMENTS.md). The build passes; rendered Stripe checkout and a real provider transaction remain unverified until setup is complete.

Day 8 adds `RideHistory` for both roles: account-owned completed/cancelled trips, cursor pagination, completed-trip PDF downloads, explicit email requests/status, and older rider payment details. Follow [history and receipts](../docs/HISTORY_RECEIPTS.md) for the local mail-catcher/worker setup. Email is disabled by default; PDF download is independent. The React build passes, while browser interaction remains a manual follow-up.

Day 9 adds **Ratings and review** on completed history entries, **Your rating**, optional plain-text comments, and saved/received feedback. `review.changed` refreshes private summaries; manual controls remain. Background history sync now keeps open review/payment forms mounted so a live refresh does not discard a draft. Follow [the review walkthrough](../docs/REVIEWS.md); browser interaction is still unverified.

Day 10 adds an optional promo form before the first checkout and a rider **Wallet balance** panel with test top-up/retry/resume controls, recent attempts and verified credits. `wallet.changed` triggers private reads; manual refresh remains available. Both checkouts reuse the test-card form. Without Stripe configuration, the balance remains readable and promos work, while top-up checkout is disabled. Follow [promos and wallet](../docs/PROMOS_WALLET.md); real Stripe and manual browser verification remain pending.

Day 11 adds section navigation, role-aware instructions, a rider booking/wallet grid that stacks on narrow screens, consistent touch controls, account-action focus, distinct IDs for repeated trip checkout forms and named history disclosures. Follow [the UI walkthrough](../docs/UI_POLISH.md). Nine jsdom/component checks passed, including selected axe structural rules and keyboard simulations. Actual visual/mobile/zoom/screen-reader checks remain pending; jsdom does not render the layout.

Day 12 keeps the same frontend/API payloads, with server-side quotas and stricter validation. Keep local Redis running, restart FastAPI with `--no-proxy-headers`, and wait when the API reports too many requests. A Redis outage returns a safe unavailable message for protected reads/writes. See [the security walkthrough](../docs/SECURITY_PERFORMANCE.md); UI and real Stripe follow-ups remain pending.

Day 13 adds two booking component journeys for a lost-response retry, completion controls, quota errors and session expiry. `npm test` now runs **11 tests** across the accessibility and booking-flow files. Backend journeys use actual local HTTP/WebSocket/worker services separately; these React tests use controlled HTTP fixtures. See [the testing walkthrough](../docs/END_TO_END_TESTING.md). No frontend feature code or package pin changes were needed.

## What each tool does

- React builds the interactive page from components.
- React DOM renders those components into the browser.
- Vite runs the local development server and creates a production build.
- npm installs the JavaScript dependencies and runs our scripts.

We are using JavaScript and plain CSS for this first learning step. Styling can be expanded when we reach the UI milestones.

## Run both apps

Keep two terminals open. Each server stays running in its own terminal.

### Terminal 1: FastAPI

```bash
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/backend"
source .venv/bin/activate
export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"
python -m uvicorn app.main:app --reload --no-proxy-headers --ws-max-size 2048
```

If FastAPI is already running on port 8000, reuse it rather than starting another copy.

### Terminal 2: React

```bash
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/frontend"
npm run dev
```

Open <http://127.0.0.1:5173>, expand **Check the app connection** near the bottom and click **Check backend connection**. With FastAPI running, the page should report:

```text
Connected! FastAPI returned a healthy response.
```

If FastAPI is stopped, the page explains that it could not reach a healthy backend. Start FastAPI and click **Check again**. Requests time out after five seconds.

Press `Ctrl+C` in each terminal when you want to stop its server. Activating a Python virtual environment alone does not start FastAPI.

## Install on another machine

Use Node.js 24, which was available for this checkpoint. From `frontend/`, run:

```bash
npm ci
npm run dev
```

`npm ci` installs the exact dependency versions from `package-lock.json`. Both `package.json` and `package-lock.json` belong in Git; `node_modules/` does not.

## How the connection works

```text
Browser -> React button -> fetch('/api/health')
        -> Vite development proxy -> FastAPI on port 8000
        -> JSON response -> updated React message
```

The browser sends the request to Vite on port 5173. Vite's `/api` proxy forwards it to `http://127.0.0.1:8000`. Keeping the browser request on the frontend's own origin avoids needing cross-origin configuration for this local step.

Since Day 5, Vite also forwards `/api` WebSocket upgrades with `ws: true` while preserving the browser Origin. The backend checks Origin on state-changing and WebSocket requests.

This proxy exists only in the development server. A deployed build will need an API routing arrangement or a configured API URL with appropriate CORS; that is part of the deployment milestone.

## Understand the files

| File | Purpose |
| --- | --- |
| `index.html` | Provides the `root` element that React renders into. |
| `src/main.jsx` | Loads styles and renders our `App` component. |
| `src/App.jsx` | Defines the page, connection state, and health request. |
| `src/AuthPanel.jsx` | Handles account forms and restores/verifies the HTTP-only cookie session through FastAPI. |
| `src/RideBooking.jsx` | Requests estimates, displays their expiry and price, saves a ride, and refreshes its status. |
| `src/DriverDashboard.jsx` | Restores the driver profile/assignment, saves vehicle details, updates availability/location, and accepts or declines nearby requests. |
| `src/useRealtime.js` | Opens the account socket, coalesces events, retries connections, and confirms location messages. |
| `src/RidePayment.jsx` | Applies an optional promo before invoice creation, prepares owner-only test checkout, and exports the reusable test-card form. |
| `src/Wallet.jsx` | Reads the rider balance/credit ledger and creates or resumes an owned test top-up; success comes from saved webhook state. |
| `src/RideHistory.jsx` | Shows owned terminal trips, grouped document actions and expandable review/payment details. |
| `src/RideReviews.jsx` | Keeps native labeled rating radios and a bounded comment form, preserving drafts during background reads. |
| `src/styles.css` | Styles the desktop and mobile layouts. |
| `vite.config.js` | Configures the React plugin, fixed frontend port, and API proxy. |
| `package.json` | Lists dependencies and development/build commands. |
| `package-lock.json` | Records exact installed dependency versions. |
| `vitest.config.js` | Runs component checks in jsdom without starting a browser or the application services. |
| `tests/accessibility.test.jsx` | Checks role-specific structure, ID/label references and selected keyboard/account/promo/review interactions against controlled API fixtures. |

In `App.jsx`, `useState('idle')` remembers the connection status. Calling `setConnection(...)` updates it and React redraws the relevant parts of the page. `fetch(...)` makes the HTTP request. We check both the HTTP response and the returned `status` value before showing success.

The button is disabled while checking, and the status message is announced to screen readers. No successful connection is assumed before a real response arrives.

## Build check

```bash
npm run build
```

Vite writes generated output into `dist/`, which is ignored by Git. A successful build confirms the app can be bundled; it does not by itself verify a running backend connection.

## Day 11 component checks

```bash
npm test
```

This originally introduced nine focused tests using pinned development tools: Vitest, jsdom, Testing Library and axe-core. Day 13 adds two booking-flow cases, for eleven total. The tests contact no backend, database or Stripe service. Color contrast/layout are excluded from the simulated axe run; the [manual checklist](../docs/UI_POLISH.md) remains necessary. See the separate [API journeys](../docs/END_TO_END_TESTING.md) for real local service coverage.

## Authentication and the Day 1 checkpoint

The user chose custom FastAPI + PostgreSQL authentication instead of an external provider. The account panel is connected to the real backend and uses an HTTP-only cookie. `App` shares the signed-in user with `RideBooking` or shows `DriverDashboard` for a driver. Changing accounts resets component state. The API restores the rider's latest open ride, falling back to their latest completed ride for checkout, or the driver's active assignment. See the progress log for verification and daily commit/push checkpoints.

References: [Vite guide](https://vite.dev/guide/) and [React's guide to starting an app](https://react.dev/learn/build-a-react-app-from-scratch).
