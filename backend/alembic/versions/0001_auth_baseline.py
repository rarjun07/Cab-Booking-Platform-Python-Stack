"""Adopt the verified Day 1 auth schema, or create it on a fresh database."""

from alembic import context, op
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from geoalchemy2 import alembic_helpers
import sqlalchemy as sa

revision = "0001_auth_baseline"
down_revision = None
branch_labels = depends_on = None


def baseline_metadata():
    """Frozen Day 1 schema: never import future ORM definitions into a revision."""
    metadata = sa.MetaData()
    sa.Table("users", metadata,
             sa.Column("id", sa.Uuid(), primary_key=True),
             sa.Column("name", sa.String(100), nullable=False),
             sa.Column("email", sa.String(254), nullable=False),
             sa.Column("password_hash", sa.String(255), nullable=False),
             sa.Column("role", sa.String(20), nullable=False),
             sa.CheckConstraint("role IN ('rider', 'driver')", name="valid_user_role"),
             sa.Index("ix_users_email", "email", unique=True))
    sa.Table("auth_sessions", metadata,
             sa.Column("id", sa.Uuid(), primary_key=True),
             sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
             sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
             sa.Column("revoked_at", sa.DateTime(timezone=True)),
             sa.Index("ix_auth_sessions_user_id", "user_id"))
    return metadata


def upgrade():
    connection = op.get_bind()
    if context.is_offline_mode():
        baseline_metadata().create_all(connection, checkfirst=False)
        return
    inspector = sa.inspect(connection)
    existing = set(inspector.get_table_names()) - {"alembic_version", "spatial_ref_sys"}
    metadata = baseline_metadata()
    if existing:
        if existing != set(metadata.tables):
            raise RuntimeError("Unversioned schema is not the Day 1 baseline; inspect it before migrating.")
        migration_context = MigrationContext.configure(connection, opts={
            "include_object": alembic_helpers.include_object, "compare_server_default": True})
        if compare_metadata(migration_context, metadata):
            raise RuntimeError("Existing auth columns/indexes/foreign keys differ from Day 1; refusing to adopt.")
        checks = inspector.get_check_constraints("users")
        if len(checks) != 1 or checks[0]["name"] != "valid_user_role":
            raise RuntimeError("The expected Day 1 role constraint is missing or changed.")
        for table in ("users", "auth_sessions"):
            if inspector.get_pk_constraint(table)["constrained_columns"] != ["id"]:
                raise RuntimeError("The Day 1 primary key differs; refusing to adopt.")
        # Compare PostgreSQL's canonical constraint definitions, not hand-normalized SQL.
        connection.exec_driver_sql("CREATE TEMP TABLE _cab_expected_role_check (role VARCHAR(20), CONSTRAINT valid_user_role CHECK (role IN ('rider', 'driver'))) ON COMMIT DROP")
        definition = sa.text("SELECT pg_get_constraintdef(oid, true) FROM pg_constraint WHERE conrelid=CAST(:table_name AS regclass) AND conname='valid_user_role'")
        expected = connection.scalar(definition, {"table_name": "pg_temp._cab_expected_role_check"})
        actual = connection.scalar(definition, {"table_name": "users"})
        if actual != expected:
            raise RuntimeError("The Day 1 role constraint definition differs; refusing to adopt.")
        return
    metadata.create_all(connection)


def downgrade():
    op.drop_table("auth_sessions")
    op.drop_table("users")
