"""Print database structure and migration status without printing credentials or user data."""

from sqlalchemy import inspect, text

from app import models  # Register GeoAlchemy's PostgreSQL geometry reflection support.
from app.database import get_engine


if __name__ == "__main__":
    with get_engine().connect() as connection:
        print("PostGIS:", connection.scalar(text("SELECT PostGIS_Version()")))
        print("Alembic revision:", connection.scalar(text("SELECT version_num FROM alembic_version")))
        inspector = inspect(connection)
        for table in sorted(set(inspector.get_table_names()) - {"spatial_ref_sys", "alembic_version"}):
            columns = inspector.get_columns(table)
            print(f"{table}: " + ", ".join(column["name"] for column in columns))
