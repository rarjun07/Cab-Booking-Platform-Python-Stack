from pathlib import Path
from decimal import Decimal
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
            assert {"users", "auth_sessions", "drivers", "rides", "payments", "reviews", "receipt_emails"} <= set(inspect(connection).get_table_names())
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0006_receipt_emails"
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


def test_day3_driver_and_ride_survive_matching_migration(test_engine):
    with test_engine.connect() as connection:
        transaction = connection.begin()
        try:
            config = config_for(connection)
            command.downgrade(config, "0003_ride_quote")
            rider_id, driver_id, ride_id, quote_id = uuid4(), uuid4(), uuid4(), uuid4()
            for user_id, role in [(rider_id, "rider"), (driver_id, "driver")]:
                connection.execute(text("INSERT INTO users (id,name,email,password_hash,role) VALUES (:id,'Legacy',:email,'keep-hash',:role)"), {"id": user_id, "email": f"{user_id}@example.com", "role": role})
            connection.execute(text("INSERT INTO drivers (user_id, current_location, status) VALUES (:id, ST_SetSRID(ST_MakePoint(77.209,28.614),4326), 'active')"), {"id": driver_id})
            connection.execute(text("INSERT INTO rides (id,rider_id,quote_id,pickup_point,drop_point,fare_estimate) VALUES (:id,:rider,:quote,ST_SetSRID(ST_MakePoint(77.209,28.6139),4326),ST_SetSRID(ST_MakePoint(77.2295,28.6129),4326),104.38)"), {"id": ride_id, "rider": rider_id, "quote": quote_id})
            command.upgrade(config, "head")
            assert connection.scalar(text("SELECT quote_id FROM rides WHERE id=:id"), {"id": ride_id}) == quote_id
            assert connection.scalar(text("SELECT fare_estimate FROM rides WHERE id=:id"), {"id": ride_id}) == Decimal("104.38")
            assert connection.scalar(text("SELECT location_updated_at FROM drivers WHERE user_id=:id"), {"id": driver_id}) is None
            assert connection.scalar(text("SELECT ST_X(current_location) FROM drivers WHERE user_id=:id"), {"id": driver_id}) == 77.209
        finally:
            transaction.rollback()


def test_existing_payment_is_preserved_when_payment_audit_fields_are_added(test_engine):
    with test_engine.connect() as connection:
        transaction = connection.begin()
        try:
            config = config_for(connection)
            command.downgrade(config, "0004_driver_matching")
            user_id, ride_id, payment_id = uuid4(), uuid4(), uuid4()
            connection.execute(text("INSERT INTO users (id,name,email,password_hash,role) VALUES (:id,'Legacy payment rider',:email,'keep-hash','rider')"), {"id": user_id, "email": f"{user_id}@example.com"})
            connection.execute(text("INSERT INTO rides (id,rider_id,status,pickup_point,drop_point,fare_estimate) VALUES (:id,:rider,'completed',ST_SetSRID(ST_MakePoint(77.209,28.6139),4326),ST_SetSRID(ST_MakePoint(77.2295,28.6129),4326),104.38)"), {"id": ride_id, "rider": user_id})
            connection.execute(text("INSERT INTO payments (id,ride_id,stripe_payment_intent_id,amount,status) VALUES (:id,:ride,'pi_preservedfixture',104.38,'succeeded')"), {"id": payment_id, "ride": ride_id})
            command.upgrade(config, "head")
            row = connection.execute(text("SELECT stripe_payment_intent_id,amount,status,currency,created_at,paid_at FROM payments WHERE id=:id"), {"id": payment_id}).one()
            assert (row.stripe_payment_intent_id, row.amount, row.status, row.currency) == ("pi_preservedfixture", Decimal("104.38"), "succeeded", "inr")
            assert row.created_at is not None and row.paid_at is None
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
