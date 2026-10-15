"""Add the booking domain and PostGIS points without replacing existing auth data."""

from alembic import context, op
from geoalchemy2 import Geometry
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002_booking_models"
down_revision = "0001_auth_baseline"
branch_labels = depends_on = None


def point():
    # Index creation is explicit below, avoiding duplicate GeoAlchemy/Alembic indexes.
    return Geometry("POINT", srid=4326, spatial_index=False)


def upgrade():
    if not context.is_offline_mode() and not op.get_bind().scalar(sa.text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='postgis')")):
        raise RuntimeError("Enable PostGIS in this database as an administrator before upgrading.")
    op.add_column("users", sa.Column("phone", sa.String(32)))
    op.add_column("users", sa.Column("profile_pic", sa.String(2048)))
    op.add_column("users", sa.Column("rating_avg", sa.Numeric(3, 2), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_unique_constraint("users_phone_key", "users", ["phone"])
    op.create_check_constraint("ck_users_rating_avg", "users", "rating_avg BETWEEN 0 AND 5")
    op.create_table("drivers",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("vehicle_info", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("current_location", point()),
        sa.Column("status", sa.String(20), nullable=False, server_default="offline"),
        sa.CheckConstraint("status IN ('active', 'offline')", name="ck_drivers_status"),
        sa.CheckConstraint("current_location IS NULL OR (ST_X(current_location) BETWEEN -180 AND 180 AND ST_Y(current_location) BETWEEN -90 AND 90)", name="ck_drivers_coordinates"))
    op.create_index("idx_drivers_current_location", "drivers", ["current_location"], postgresql_using="gist")
    op.create_table("rides",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("rider_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("driver_id", sa.Uuid(), sa.ForeignKey("drivers.user_id", ondelete="SET NULL")),
        sa.Column("pickup_point", point(), nullable=False),
        sa.Column("drop_point", point(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="requested"),
        sa.Column("fare_estimate", sa.Numeric(10, 2), nullable=False),
        sa.Column("fare_actual", sa.Numeric(10, 2)),
        sa.Column("distance_meters", sa.Integer()),
        sa.Column("duration_secs", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('requested', 'accepted', 'arriving', 'in_progress', 'completed', 'cancelled')", name="ck_rides_status"),
        sa.CheckConstraint("fare_estimate >= 0 AND (fare_actual IS NULL OR fare_actual >= 0)", name="ck_rides_fares"),
        sa.CheckConstraint("distance_meters IS NULL OR distance_meters >= 0", name="ck_rides_distance"),
        sa.CheckConstraint("duration_secs IS NULL OR duration_secs >= 0", name="ck_rides_duration"),
        sa.CheckConstraint("driver_id IS NULL OR rider_id <> driver_id", name="ck_rides_distinct_participants"),
        sa.CheckConstraint("ST_X(pickup_point) BETWEEN -180 AND 180 AND ST_Y(pickup_point) BETWEEN -90 AND 90 AND ST_X(drop_point) BETWEEN -180 AND 180 AND ST_Y(drop_point) BETWEEN -90 AND 90", name="ck_rides_coordinates"))
    op.create_index("ix_rides_driver_id", "rides", ["driver_id"])
    op.create_index("ix_rides_rider_created", "rides", ["rider_id", "created_at"])
    op.create_index("idx_rides_pickup_point", "rides", ["pickup_point"], postgresql_using="gist")
    op.create_index("idx_rides_drop_point", "rides", ["drop_point"], postgresql_using="gist")
    op.create_table("payments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("ride_id", sa.Uuid(), sa.ForeignKey("rides.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("stripe_payment_intent_id", sa.String(255), unique=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.CheckConstraint("amount >= 0", name="ck_payments_amount"),
        sa.CheckConstraint("status IN ('pending', 'processing', 'succeeded', 'failed', 'cancelled', 'refunded')", name="ck_payments_status"))
    op.create_table("reviews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("ride_id", sa.Uuid(), sa.ForeignKey("rides.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("rater_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("rated_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating"),
        sa.CheckConstraint("rater_id <> rated_id", name="ck_reviews_distinct_users"),
        sa.CheckConstraint("comment IS NULL OR length(comment) <= 2000", name="ck_reviews_comment_length"),
        sa.UniqueConstraint("ride_id", "rater_id", name="uq_reviews_ride_rater"))
    op.create_index("ix_reviews_rater_id", "reviews", ["rater_id"])
    op.create_index("ix_reviews_rated_id", "reviews", ["rated_id"])


def downgrade():
    for table in ("reviews", "payments", "rides", "drivers"):
        op.drop_table(table)
    op.drop_constraint("ck_users_rating_avg", "users", type_="check")
    op.drop_constraint("users_phone_key", "users", type_="unique")
    for column in ("created_at", "rating_avg", "profile_pic", "phone"):
        op.drop_column("users", column)
    # PostGIS is administrator-managed and deliberately remains installed.
