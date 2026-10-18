"""Indexes for participant history, wallet pages, and promo usage counts."""
from alembic import op
import sqlalchemy as sa

revision = "0009_query_indexes"
down_revision = "0008_promos_wallet"
branch_labels = depends_on = None


def upgrade():
    for role in ("rider", "driver"):
        op.create_index(f"ix_rides_{role}_history", "rides", [f"{role}_id", sa.text("created_at DESC"), sa.text("id DESC")],
                        postgresql_where=sa.text("status IN ('completed', 'cancelled')"))
    for table in ("wallet_topups", "wallet_entries"):
        op.create_index(f"ix_{table}_owner_created", table, ["user_id", sa.text("created_at DESC"), sa.text("id DESC")])
        op.drop_index(f"ix_{table}_user_id", table_name=table)
    op.create_index("ix_promo_redemptions_code_user", "promo_redemptions", ["promo_id", "user_id"])
    op.drop_index("ix_promo_redemptions_promo_id", table_name="promo_redemptions")


def downgrade():
    op.create_index("ix_promo_redemptions_promo_id", "promo_redemptions", ["promo_id"])
    op.drop_index("ix_promo_redemptions_code_user", table_name="promo_redemptions")
    for table in ("wallet_topups", "wallet_entries"):
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])
        op.drop_index(f"ix_{table}_owner_created", table_name=table)
    for role in ("rider", "driver"):
        op.drop_index(f"ix_rides_{role}_history", table_name="rides")
