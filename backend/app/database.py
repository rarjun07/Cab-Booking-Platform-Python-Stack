"""PostgreSQL connection and request-scoped database sessions."""

from functools import lru_cache

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Session

from app.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine():
    return create_engine(
        get_settings().database_url.get_secret_value(),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )


def get_db():
    try:
        with Session(get_engine()) as session:
            yield session
    except OperationalError:
        raise HTTPException(503, "Database unavailable. Please try again later.") from None
