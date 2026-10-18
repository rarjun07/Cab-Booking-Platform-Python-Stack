"""Promo redemptions, test-wallet top-ups, and one shared Stripe event audit."""
from alembic import op
import sqlalchemy as sa

revision = "0008_promos_wallet"
down_revision = "0007_review_timestamps"
branch_labels = depends_on = None


def upgrade():
    op.add_column("users", sa.Column("wallet_balance", sa.Numeric(14, 2), server_default="0", nullable=False))
    op.create_check_constraint("ck_users_wallet_balance", "users", "wallet_balance >= 0")
    op.create_table("promo_codes",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("code", sa.String(20), nullable=False),
        sa.Column("percent_off", sa.SmallInteger(), nullable=False), sa.Column("min_fare", sa.Numeric(10, 2), nullable=False),
        sa.Column("max_discount", sa.Numeric(10, 2), nullable=False), sa.Column("max_uses", sa.Integer(), nullable=False),
        sa.Column("per_user_limit", sa.Integer(), nullable=False), sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code", name="uq_promo_codes_code"),
        sa.CheckConstraint("code ~ '^[A-Z0-9]{3,20}$'", name="ck_promo_codes_code"),
        sa.CheckConstraint("percent_off BETWEEN 1 AND 90", name="ck_promo_codes_percent"),
        sa.CheckConstraint("min_fare >= 0 AND max_discount > 0", name="ck_promo_codes_amounts"),
        sa.CheckConstraint("max_uses > 0 AND per_user_limit > 0 AND per_user_limit <= max_uses", name="ck_promo_codes_limits"),
        sa.CheckConstraint("expires_at > starts_at", name="ck_promo_codes_dates"))
    op.create_table("promo_redemptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("promo_id", sa.Uuid(), sa.ForeignKey("promo_codes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("ride_id", sa.Uuid(), sa.ForeignKey("rides.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("code", sa.String(20), nullable=False), sa.Column("base_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(10, 2), nullable=False), sa.Column("final_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("base_amount > 0 AND discount_amount > 0 AND final_amount >= 50 AND base_amount = discount_amount + final_amount", name="ck_promo_redemptions_amounts"))
    for column in ("promo_id", "user_id"):
        op.create_index(f"ix_promo_redemptions_{column}", "promo_redemptions", [column])
    op.create_table("wallet_topups",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("request_key", sa.Uuid(), nullable=False), sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="inr", nullable=False),
        sa.Column("stripe_payment_intent_id", sa.String(255), unique=True),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("credited_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "request_key", name="uq_wallet_topups_request"),
        sa.CheckConstraint("amount BETWEEN 50 AND 10000 AND currency = 'inr'", name="ck_wallet_topups_amount"),
        sa.CheckConstraint("status IN ('pending','processing','succeeded','failed','cancelled')", name="ck_wallet_topups_status"))
    op.create_index("ix_wallet_topups_user_id", "wallet_topups", ["user_id"])
    op.create_table("wallet_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("topup_id", sa.Uuid(), sa.ForeignKey("wallet_topups.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("topup_id", name="uq_wallet_entries_topup"),
        sa.CheckConstraint("amount > 0", name="ck_wallet_entries_amount"))
    op.create_index("ix_wallet_entries_user_id", "wallet_entries", ["user_id"])
    op.alter_column("payment_events", "payment_id", nullable=True)
    op.add_column("payment_events", sa.Column("wallet_topup_id", sa.Uuid(), sa.ForeignKey("wallet_topups.id", ondelete="RESTRICT")))
    op.create_index("ix_payment_events_wallet_topup_id", "payment_events", ["wallet_topup_id"])
    op.create_check_constraint("ck_payment_events_target", "payment_events", "(payment_id IS NOT NULL AND wallet_topup_id IS NULL) OR (payment_id IS NULL AND wallet_topup_id IS NOT NULL)")


def downgrade():
    op.execute("DELETE FROM payment_events WHERE wallet_topup_id IS NOT NULL")
    op.drop_constraint("ck_payment_events_target", "payment_events", type_="check")
    op.drop_index("ix_payment_events_wallet_topup_id", table_name="payment_events")
    op.drop_column("payment_events", "wallet_topup_id")
    op.alter_column("payment_events", "payment_id", nullable=False)
    op.drop_index("ix_wallet_entries_user_id", table_name="wallet_entries")
    op.drop_table("wallet_entries")
    op.drop_index("ix_wallet_topups_user_id", table_name="wallet_topups")
    op.drop_table("wallet_topups")
    for column in ("user_id", "promo_id"):
        op.drop_index(f"ix_promo_redemptions_{column}", table_name="promo_redemptions")
    op.drop_table("promo_redemptions")
    op.drop_table("promo_codes")
    op.drop_constraint("ck_users_wallet_balance", "users", type_="check")
    op.drop_column("users", "wallet_balance")
