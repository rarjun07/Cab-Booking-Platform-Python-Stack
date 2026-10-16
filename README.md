# Cab Booking Platform

An internship project based on the mentor's **Cab Booking Platform - Python Stack** guide.

## Agreed stack

- Backend: Python with FastAPI.
- Database: PostgreSQL; add PostGIS for the guide's location queries.
- Frontend: React. The guide lists Next.js as optional, so Next.js is not required for this project.
- Authentication: custom FastAPI + PostgreSQL, with Argon2 password hashes and signed HTTP-only session cookies, as chosen by the user instead of Clerk/Supabase Auth.
- Routing: OSRM with OpenStreetMap data, the user's free alternative to Google Maps.
- Realtime: FastAPI WebSockets backed by Redis Pub/Sub.
- Additional services will be introduced on their scheduled days: Stripe, Celery, and Docker.

## How we will work

Work through one project day at a time. For each day:

1. Explain the goal and the code being added.
2. Implement only the current day's scope.
3. Run relevant checks and demonstrate the result.
4. Review the changes and update the progress log.
5. Commit the day's work and push it to the user's GitHub repository.
6. Verify the pushed commit before starting the next day.

The GitHub repository is [rarjun07/Cab-Booking-Platform-Python-Stack](https://github.com/rarjun07/Cab-Booking-Platform-Python-Stack). GitHub access is verified, and the local Git remote `origin` points to this repository.

Learning preference: step-by-step guidance with explanations.

## Project documents

- [14-day roadmap](docs/ROADMAP.md)
- [Progress and Git checkpoints](docs/PROGRESS.md)
- [Backend setup and code explanation](backend/README.md)
- [Frontend setup and code explanation](frontend/README.md)
- [Authentication setup and walkthrough](docs/AUTHENTICATION.md)
- [Database models, PostGIS, and migrations](docs/DATABASE.md)
- [Fare estimates and ride requests](docs/RIDE_BOOKING.md)
- [Driver dashboard and nearby matching](docs/RIDE_MATCHING.md)
- [Live ride and location updates](docs/LIVE_UPDATES.md)

## Current state

Days 1-4 are implemented and pushed. The user also chose to include Day 5: authenticated FastAPI WebSockets, Redis notifications, live location/status updates, reconnect recovery, and guarded trip progression. All 113 backend tests and the React build pass. A live demo verified Vite WebSocket forwarding and Redis delivery between two independent backend processes. Manual UI checks remain pending after the earlier browser URL-policy rejection; the user has not tried the live connection badge yet. The Day 5 Git checkpoint is pending. Day 6 payments have not started.
