"""Tests use the dedicated PostgreSQL test database and roll back each test."""

from pathlib import Path
import os

from dotenv import dotenv_values
from alembic import command
from alembic.config import Config
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.main import app


@pytest.fixture(scope="session")
def test_engine():
    local = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
    url = os.environ.get("TEST_DATABASE_URL") or local.get("TEST_DATABASE_URL")
    if not url:
        pytest.fail("Set TEST_DATABASE_URL to a dedicated PostgreSQL database ending in _test.")
    parsed = make_url(url)
    dev_url = os.environ.get("DATABASE_URL") or local.get("DATABASE_URL")
    if (parsed.get_backend_name() != "postgresql" or not (parsed.database or "").endswith("_test")
            or (dev_url and parsed.database == make_url(dev_url).database)):
        pytest.fail("Refusing to run tests outside a separate PostgreSQL _test database.")
    engine = create_engine(url, connect_args={"connect_timeout": 5})
    with engine.begin() as connection:
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    yield engine
    engine.dispose()


@pytest.fixture
def db(test_engine):
    with test_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()


@pytest.fixture
def client(db):
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app, headers={"Origin": "http://127.0.0.1:5173"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def account():
    return {"name": "Test Rider", "email": "rider@example.com",
            "password": "test-password-long-enough", "role": "rider"}
