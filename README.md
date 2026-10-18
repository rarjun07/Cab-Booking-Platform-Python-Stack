# Cab Booking Platform

An internship project based on the mentor's **Cab Booking Platform - Python Stack** guide.

## Agreed stack

- Backend: Python with FastAPI.
- Database: PostgreSQL; add PostGIS for the guide's location queries.
- Frontend: React. The guide lists Next.js as optional, so Next.js is not required for this project.
- Authentication: custom FastAPI + PostgreSQL, with Argon2 password hashes and signed HTTP-only session cookies, as chosen by the user instead of Clerk/Supabase Auth.
- Routing: OSRM with OpenStreetMap data, the user's free alternative to Google Maps.
- Realtime: FastAPI WebSockets backed by Redis Pub/Sub.
- Payments: Stripe sandbox integration is in progress; real provider verification remains pending.
- Background jobs: Celery with the existing Redis broker; SMTP receipt delivery can be tested with a local mail catcher.
- Docker remains scheduled for Day 14.

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
- [Stripe test-payment setup and verification](docs/PAYMENTS.md)
- [First-week tests and manual checklist](docs/TESTING.md)
- [Ride history, PDF receipts, and local receipt email](docs/HISTORY_RECEIPTS.md)
- [Ratings and reviews](docs/REVIEWS.md)
- [Promo codes and test-wallet top-ups](docs/PROMOS_WALLET.md)

## Current state

Days 1-7 code checkpoints are pushed and verified. The user explicitly deferred Day 6 Stripe setup, a real test transaction, Stripe-delivered webhooks, and rendered checkout verification on 2026-10-18; payment-provider calls in automated tests use a controlled double.

Day 8 history/PDF/Celery email and Day 9 ratings/reviews code checkpoints are pushed and verified. Email is disabled by default with a free local-catcher setup in its walkthrough.

Day 10 adds server-priced promo discounts before invoice creation, discount snapshots in trip PDFs, and rider test-wallet top-ups with durable retries, an atomic credit ledger and private live refresh. The schema is at `0008_promos_wallet`; no new dependency or secret is needed beyond the existing optional Stripe configuration. All 230 backend tests, the React build, dependency and schema checks pass. Day 10's Git checkpoint is pending. Browser interaction and earlier manual UI follow-ups remain unverified; actual Stripe ride/top-up verification remains deferred. Day 11 has not started.
