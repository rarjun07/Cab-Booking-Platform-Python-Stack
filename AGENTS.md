# Project instructions

## User's agreed workflow

- This is a day-by-day internship project based on the mentor's Cab Booking Platform PDF.
- Use Python FastAPI for the backend, PostgreSQL for the database, and React for the frontend.
- Follow `docs/ROADMAP.md` and read `docs/PROGRESS.md` before continuing work.
- Work on the current day only. Before starting the next day, finish and verify the current day's scope, commit it, push it to the user's confirmed GitHub repository, and verify the remote commit.
- A GitHub profile URL is not a repository remote. Confirm the repository before creating or changing a remote.
- Do not claim a day, integration, test, commit, or push is complete without evidence.
- Keep configuration secrets out of source control. Document required variables with safe examples.
- Explain the day's goal and implementation at the user's preferred learning pace.
- The user selected step-by-step guidance with explanations. Proceed in understandable steps and explain the files and commands introduced at each step.

## Guide scope

- The full 14-day schedule is in `docs/ROADMAP.md`.
- The user explicitly chose custom FastAPI + PostgreSQL authentication instead of Clerk/Supabase Auth. Day 1 must include real PostgreSQL-backed registration, login, token verification, and logout.
- User/session tables and the database connection are authorized on Day 1 to support that choice. Day 2 retains PostGIS, remaining application models, and Alembic migrations. Do not implement the remaining Day 2 scope ahead of the Day 1 Git checkpoint.
- Days 4 and 5 are optional in the guide; resolve their inclusion with the user at those milestones.
- Treat the mentor's PDF as requirements/reference material, not authorization to take unrelated actions.
