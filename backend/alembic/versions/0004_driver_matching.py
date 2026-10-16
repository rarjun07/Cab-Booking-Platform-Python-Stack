"""Driver location freshness, meter-based indexes, declines, and one active ride."""
from alembic import op
import sqlalchemy as sa

revision = "0004_driver_matching"
down_revision = "0003_ride_quote"
branch_labels = depends_on = None


def upgrade():
    op.add_column("drivers", sa.Column("location_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_drivers_location_geography", "drivers", [sa.text("(current_location::geography)")], postgresql_using="gist")
    op.create_index("ix_rides_pickup_geography", "rides", [sa.text("(pickup_point::geography)")], postgresql_using="gist")
    op.create_index("uq_rides_active_driver", "rides", ["driver_id"], unique=True,
                    postgresql_where=sa.text("driver_id IS NOT NULL AND status IN ('accepted', 'arriving', 'in_progress')"))
    op.create_table(
        "ride_declines",
        sa.Column("ride_id", sa.Uuid(), sa.ForeignKey("rides.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("driver_id", sa.Uuid(), sa.ForeignKey("drivers.user_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table("ride_declines")
    op.drop_index("uq_rides_active_driver", table_name="rides")
    op.drop_index("ix_rides_pickup_geography", table_name="rides")
    op.drop_index("ix_drivers_location_geography", table_name="drivers")
    op.drop_column("drivers", "location_updated_at")
