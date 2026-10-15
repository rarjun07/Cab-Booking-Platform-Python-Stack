# Internship roadmap

Source: the mentor's nine-page **Cab Booking Platform - Python Stack** PDF, particularly the schedule on pages 4-5 and the React / optional Next.js stack on page 8.

This is the guide's sequence adapted to the user's choices: Python FastAPI, PostgreSQL, and React. Each day is a work milestone, not a promise that its scope takes one calendar day. Do not skip unfinished work merely to keep the two-week timeline.

The user subsequently chose custom FastAPI + PostgreSQL authentication instead of the guide's Clerk/Supabase Auth options. The database connection and user/session tables move into Day 1 to support it; the remaining Day 2 scope is unchanged.

## Daily plan

| Day | Scope from the guide | Evidence before the daily Git checkpoint |
| --- | --- | --- |
| 1 | Initialize `backend/` and `frontend/`; FastAPI scaffold; custom PostgreSQL-backed authentication and signed session verification (user's adaptation). | Both apps run; real registration/login/logout work; FastAPI rejects invalid, missing, expired, and revoked sessions. |
| 2 | Extend the PostgreSQL setup with PostGIS, remaining SQLAlchemy models, and Alembic migrations. | Migrations include the existing auth schema and add driver, ride, payment, and review models; the geospatial setup is verified. |
| 3 | Fare estimation with Google Maps and ride request creation. | An estimate can be requested and a ride request persists in PostgreSQL. |
| 4 | Optional driver dashboard, nearby-driver queries, matching, and availability. | If included, availability and nearby-driver matching work with sample data. If deferred, record the decision before proceeding. |
| 5 | Optional realtime rider/driver connections and location updates with WebSockets or Socket.IO plus Redis. | If included, an authenticated rider receives the relevant driver's updates. If deferred, record the decision before proceeding. |
| 6 | Stripe PaymentIntents and signed payment webhooks. | Stripe test-mode payment flow works and verified webhook events update payment state. |
| 7 | Buffer, endpoint tests, and manual flow checks. | Tests pass and issues found in the first week's implemented flows are resolved or explicitly tracked. |
| 8 | Ride history, PDF receipts, and Celery receipt-email tasks. | A completed ride appears in history, has a readable receipt, and can trigger the configured background email task. |
| 9 | Ratings and reviews with aggregation. | Authorized participants can submit valid reviews and rating summaries update correctly. |
| 10 | Promo codes and wallet top-ups using Stripe. | Promo rules and balances work; a verified test payment credits the wallet once. |
| 11 | React UI polish, accessibility, and mobile responsiveness. | Implemented screens work on desktop and mobile and support keyboard interaction. |
| 12 | Redis rate limits, CORS, validation, database indexes, and query performance. | Relevant security and performance checks pass for the implemented features. |
| 13 | End-to-end tests and multiple-driver / multiple-ride scenarios. | Core end-to-end flows pass; test coverage reflects any optional features actually included. |
| 14 | Dockerfiles, local Compose services, and deployment. | Container startup is verified and the configured deployed application passes smoke checks. |

Days 4 and 5 are explicitly optional in the guide. The guide also labels geospatial queries optional in its notes, while its Day 2 schedule includes PostGIS setup. Keep PostGIS in the planned database setup; decide the optional matching features when reaching Day 4.

## Day 1 checklist

- [x] Confirm the project repository URL and local GitHub access.
- [x] Set up Git and a `.gitignore`.
- [x] Add safe environment-variable examples when authentication configuration is introduced.
- [x] Create the `backend/` FastAPI application and development environment.
- [x] Create the `frontend/` React application.
- [x] Confirm custom FastAPI + PostgreSQL authentication (user's explicit choice replacing the guide's provider options).
- [x] Configure dedicated development/test databases and ignored local secrets.
- [x] Implement frontend registration, sign-in, and sign-out.
- [x] Verify signed tokens and PostgreSQL sessions in FastAPI and add a protected session endpoint.
- [x] Check frontend-to-backend connectivity and authentication success and failure paths.
- [x] Document local startup steps and explain the files added.
- [x] Record verification results in `PROGRESS.md`.
- [x] Commit Day 1 with a descriptive commit message.
- [x] Push Day 1 to the confirmed repository and verify the remote application commit (`dcf9340`).

Do not begin the remaining Day 2 database models or migrations until every required Day 1 item, including the push, is complete. Authentication must work with real PostgreSQL persistence; placeholder screens or mocked tokens do not satisfy it.

## Choices to resolve at the relevant milestone

- Day 1 choices resolved: step-by-step teaching, confirmed GitHub repository, custom FastAPI/PostgreSQL authentication, and SQLAlchemy with local PostgreSQL.
- Day 2: extend the schema with PostGIS and Alembic migrations.
- Day 3: maps API configuration. The guide mentions Leaflet for an MVP; a map display alone does not replace a routing/distance service for fare estimates.
- Days 4-5: whether to include the optional driver dashboard and realtime features.
- Day 6 onward: required service configuration for test payments, email, and deployment.

The PDF supplies project requirements and suggestions. The user's chosen stack and daily commit/push workflow govern our implementation. External credentials, accounts, and deployments are not assumed to exist merely because the PDF mentions them.
