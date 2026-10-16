"""Application entry point for the Cab Booking Platform API."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.auth import router as auth_router
from app.rides import router as rides_router
from app.drivers import router as drivers_router
from app.events import get_event_publisher
from app.realtime import router as realtime_router


@asynccontextmanager
async def lifespan(app):
    yield
    get_event_publisher().close()

app = FastAPI(title="Cab Booking Platform API", version="0.1.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(rides_router)
app.include_router(drivers_router)
app.include_router(realtime_router)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc):
    # FastAPI's default validation errors echo invalid inputs, which can include passwords.
    errors = [{key: error[key] for key in ("loc", "msg", "type")} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.get("/api/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Confirm the API is running; this does not check a database yet."""
    return {"status": "ok"}
