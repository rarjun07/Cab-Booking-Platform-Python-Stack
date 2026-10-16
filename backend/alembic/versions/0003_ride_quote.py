"""Prevent duplicate ride requests made with the same signed fare quote."""
from alembic import op
import sqlalchemy as sa

revision = "0003_ride_quote"
down_revision = "0002_booking_models"
branch_labels = depends_on = None


def upgrade():
    op.add_column("rides", sa.Column("quote_id", sa.Uuid(), nullable=True))
    op.create_unique_constraint("rides_quote_id_key", "rides", ["quote_id"])


def downgrade():
    op.drop_constraint("rides_quote_id_key", "rides", type_="unique")
    op.drop_column("rides", "quote_id")
