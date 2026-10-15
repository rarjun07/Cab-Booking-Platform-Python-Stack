# FastAPI backend

The original health endpoint below is now joined by PostgreSQL-backed registration, login, session verification, and logout. See [the authentication walkthrough](../docs/AUTHENTICATION.md) for database setup, the new files, and tests.

## What we added

- `.venv/`: this project's isolated Python environment. It holds installed libraries locally and is ignored by Git.
- `app/__init__.py`: marks `app` as a Python package.
- `app/main.py`: creates the FastAPI application and defines its first endpoint.
- `requirements.txt`: records the installed dependency versions so another developer can reproduce the environment.

FastAPI defines the API. Uvicorn runs it as a local web server.

## Set up on another machine

Use Python 3.14 for the environment verified at this checkpoint. From the project root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run locally

From the project root:

```bash
cd backend
source .venv/bin/activate
python -m uvicorn app.main:app --reload
```

If your terminal is already inside `backend/`, skip `cd backend`.

- Health endpoint: <http://127.0.0.1:8000/api/health>
- Interactive API documentation: <http://127.0.0.1:8000/docs>

The health endpoint should return:

```json
{"status":"ok"}
```

Press `Ctrl+C` to stop the server. Run `deactivate` to leave the virtual environment.

## Understand the code

1. `from fastapi import FastAPI` imports the framework's application class.
2. `app = FastAPI(...)` creates our API application.
3. `@app.get("/api/health")` registers a URL that accepts HTTP GET requests.
4. `health_check()` runs when someone requests that URL.
5. The returned Python dictionary is sent as JSON.

In the startup command, `app.main:app` means "import the `app` object from `app/main.py`." `--reload` restarts the development server when you change Python code.

The root URL `/` currently returns 404 because we only defined `/api/health`.

## Scope of this checkpoint

The health endpoint checks API availability only. Custom authentication now uses PostgreSQL user/session tables, as requested by the user. PostGIS, remaining application models, and migrations belong to Day 2. See the progress log for the current Git checkpoint.

Reference: [FastAPI's official first-steps tutorial](https://fastapi.tiangolo.com/tutorial/first-steps/).
