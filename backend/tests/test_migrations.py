from pathlib import Path
from uuid import uuid4
import io

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import inspect, text


def config_for(connection):
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.attributes["connection"] = connection
    return config


def test_fresh_database_upgrade_and_downgrade_are_transactional(test_engine):
    # test_engine is guarded to require a separate _test database. All DDL is rolled back.
    with test_engine.connect() as connection:
        transaction = connection.begin()
        try:
            config = config_for(connection)
            command.downgrade(config, "base")
            assert "users" not in inspect(connection).get_table_names()
            command.upgrade(config, "head")
            assert {"users", "auth_sessions", "drivers", "rides", "payments", "reviews"} <= set(inspect(connection).get_table_names())
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0003_ride_quote"
            command.check(config)
        finally:
            transaction.rollback()


def test_day1_account_survives_booking_schema_upgrade(test_engine):
    with test_engine.connect() as connection:
        transaction = connection.begin()
        try:
            config = config_for(connection)
            command.downgrade(config, "0001_auth_baseline")
            user_id, session_id = uuid4(), uuid4()
            connection.execute(text("INSERT INTO users (id, name, email, password_hash, role) VALUES (:id, 'Legacy rider', 'legacy-migration@example.com', 'preserve-this-hash', 'rider')"), {"id": user_id})
            connection.execute(text("INSERT INTO auth_sessions (id, user_id, expires_at) VALUES (:id, :user, now() + interval '1 hour')"), {"id": session_id, "user": user_id})
            # Simulate the real Day 1 schema, which had no Alembic version record.
            connection.execute(text("DELETE FROM alembic_version"))
            command.upgrade(config, "head")
            row = connection.execute(text("SELECT password_hash, rating_avg, created_at FROM users WHERE id=:id"), {"id": user_id}).one()
            assert row.password_hash == "preserve-this-hash"
            assert row.rating_avg == 0 and row.created_at is not None
            assert connection.scalar(text("SELECT user_id FROM auth_sessions WHERE id=:id"), {"id": session_id}) == user_id
        finally:
            transaction.rollback()


@pytest.mark.parametrize("changes", [
    ["ALTER TABLE users ALTER COLUMN name TYPE VARCHAR(99)"],
    ["ALTER TABLE users DROP CONSTRAINT valid_user_role", "ALTER TABLE users ADD CONSTRAINT valid_user_role CHECK (role IN ('rider', 'driver', 'admin'))"],
])
def test_unversioned_baseline_drift_is_not_silently_adopted(test_engine, changes):
    with test_engine.connect() as connection:
        transaction = connection.begin()
        try:
            config = config_for(connection)
            command.downgrade(config, "0001_auth_baseline")
            connection.execute(text("DELETE FROM alembic_version"))
            for statement in changes:
                connection.execute(text(statement))
            with pytest.raises(RuntimeError, match="differ"):
                command.upgrade(config, "head")
        finally:
            transaction.rollback()


def test_fresh_schema_can_be_rendered_as_sql_without_a_connection():
    output = io.StringIO()
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"), output_buffer=output)
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE users" in sql
    assert "CREATE TABLE rides" in sql
    assert "CREATE INDEX idx_drivers_current_location" in sql
