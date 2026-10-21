"""Record operator driver approvals and revocations without changing existing data."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_driver_verifications"
down_revision = "0009_query_indexes"
branch_labels = depends_on = None


def upgrade():
    op.create_table("driver_verifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("driver_id", sa.Uuid(), sa.ForeignKey("drivers.user_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=False),
        sa.Column("vehicle_info", postgresql.JSONB(), nullable=False),
        sa.Column("operator", sa.String(100), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("length(operator) BETWEEN 1 AND 100", name="ck_driver_verifications_operator"),
        sa.CheckConstraint("length(reason) BETWEEN 1 AND 500", name="ck_driver_verifications_reason"))
    op.create_index("ix_driver_verifications_driver_id", "driver_verifications", ["driver_id"])


def downgrade():
    op.drop_index("ix_driver_verifications_driver_id", table_name="driver_verifications")
    op.drop_table("driver_verifications")
