"""Payment currency, timestamps, and signed-webhook deduplication records."""
from alembic import op
import sqlalchemy as sa

revision = "0005_test_payments"
down_revision = "0004_driver_matching"
branch_labels = depends_on = None


def upgrade():
    op.add_column("payments", sa.Column("currency", sa.String(3), server_default="inr", nullable=False))
    op.add_column("payments", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column("payments", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint("ck_payments_currency", "payments", "currency = 'inr'")
    op.create_table("payment_events",
        sa.Column("stripe_event_id", sa.String(255), primary_key=True),
        sa.Column("payment_id", sa.Uuid(), sa.ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_payment_events_payment_id", "payment_events", ["payment_id"])


def downgrade():
    op.drop_index("ix_payment_events_payment_id", table_name="payment_events")
    op.drop_table("payment_events")
    op.drop_constraint("ck_payments_currency", "payments", type_="check")
    op.drop_column("payments", "paid_at")
    op.drop_column("payments", "created_at")
    op.drop_column("payments", "currency")
