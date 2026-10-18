"""Application entry point for the Cab Booking Platform API."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.auth import router as auth_router
from app.rides import router as rides_router
from app.drivers import router as drivers_router
from app.events import get_event_publisher
from app.realtime import router as realtime_router
from app.payments import router as payments_router
from app.history import router as history_router
from app.reviews import router as reviews_router
from app.promos import router as promos_router
from app.wallet import router as wallet_router
from app.config import get_settings
from app.security import RequestGuard, get_rate_limiter


@asynccontextmanager
async def lifespan(app):
    yield
    get_event_publisher().close()
    get_rate_limiter().close()
    get_rate_limiter.cache_clear()

app = FastAPI(title="Cab Booking Platform API", version="0.1.0", lifespan=lifespan)
app.add_middleware(RequestGuard)
app.add_middleware(CORSMiddleware, allow_origins=get_settings().allowed_origins, allow_credentials=True,
                   allow_methods=["GET", "POST", "PUT"], allow_headers=["Content-Type"],
                   expose_headers=["Retry-After"], max_age=600)
app.include_router(auth_router)
app.include_router(rides_router)
app.include_router(drivers_router)
app.include_router(realtime_router)
app.include_router(payments_router)
app.include_router(history_router)
app.include_router(reviews_router)
app.include_router(promos_router)
app.include_router(wallet_router)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc):
    # FastAPI's default validation errors echo invalid inputs, which can include passwords.
    errors = [{key: error[key] for key in ("loc", "msg", "type")} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.get("/api/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Confirm the API is running; this does not check a database yet."""
    return {"status": "ok"}
