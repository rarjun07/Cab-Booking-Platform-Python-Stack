"""Alembic configuration with environment-based credentials and PostGIS helpers."""

from alembic import context
from geoalchemy2 import alembic_helpers
from sqlalchemy import create_engine, pool

from app import models
from app.config import get_settings
from app.database import Base

config = context.config
target_metadata = Base.metadata


def configure(connection=None, url=None):
    context.configure(
        connection=connection, url=url, target_metadata=target_metadata,
        literal_binds=connection is None,
        compare_type=True, compare_server_default=True,
        include_object=alembic_helpers.include_object,
        process_revision_directives=alembic_helpers.writer,
        render_item=alembic_helpers.render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    configure(url=get_settings().database_url.get_secret_value())
elif config.attributes.get("connection") is not None:
    configure(connection=config.attributes["connection"])
else:
    engine = create_engine(get_settings().database_url.get_secret_value(), poolclass=pool.NullPool,
                           connect_args={"connect_timeout": 5})
    with engine.connect() as connection:
        configure(connection=connection)
    engine.dispose()
