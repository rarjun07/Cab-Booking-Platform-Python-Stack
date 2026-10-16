# React frontend

The page now includes PostgreSQL-backed sign-up, sign-in, session restoration, verification, and sign-out. See [the authentication walkthrough](../docs/AUTHENTICATION.md).

Day 3 adds a coordinate form, public Delhi sample, fare breakdown, ride request, and status refresh for signed-in riders. See [the ride-booking walkthrough](../docs/RIDE_BOOKING.md) for a step-by-step demo. The production build passes; the new form's visual/manual browser check remains pending.

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
python -m uvicorn app.main:app --reload
```

If FastAPI is already running on port 8000, reuse it rather than starting another copy.

### Terminal 2: React

```bash
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/frontend"
npm run dev
```

Open <http://127.0.0.1:5173> and click **Check backend connection**. With FastAPI running, the page should report:

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

This proxy exists only in the development server. A deployed build will need an API routing arrangement or a configured API URL with appropriate CORS; that is part of the deployment milestone.

## Understand the files

| File | Purpose |
| --- | --- |
| `index.html` | Provides the `root` element that React renders into. |
| `src/main.jsx` | Loads styles and renders our `App` component. |
| `src/App.jsx` | Defines the page, connection state, and health request. |
| `src/AuthPanel.jsx` | Handles account forms and restores/verifies the HTTP-only cookie session through FastAPI. |
| `src/RideBooking.jsx` | Requests estimates, displays their expiry and price, saves a ride, and refreshes its status. |
| `src/styles.css` | Styles the desktop and mobile layouts. |
| `vite.config.js` | Configures the React plugin, fixed frontend port, and API proxy. |
| `package.json` | Lists dependencies and development/build commands. |
| `package-lock.json` | Records exact installed dependency versions. |

In `App.jsx`, `useState('idle')` remembers the connection status. Calling `setConnection(...)` updates it and React redraws the relevant parts of the page. `fetch(...)` makes the HTTP request. We check both the HTTP response and the returned `status` value before showing success.

The button is disabled while checking, and the status message is announced to screen readers. No successful connection is assumed before a real response arrives.

## Build check

```bash
npm run build
```

Vite writes generated output into `dist/`, which is ignored by Git. A successful build confirms the app can be bundled; it does not by itself verify a running backend connection.

## Authentication and the Day 1 checkpoint

The user chose custom FastAPI + PostgreSQL authentication instead of an external provider. The account panel is connected to the real backend and uses an HTTP-only cookie. `App` shares the signed-in user with `RideBooking`; changing accounts resets the booking state. Database models arrived on Day 2 and the ride request flow on Day 3. See the progress log for verification and daily commit/push checkpoints.

References: [Vite guide](https://vite.dev/guide/) and [React's guide to starting an app](https://react.dev/learn/build-a-react-app-from-scratch).
