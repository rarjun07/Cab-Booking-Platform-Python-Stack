"""Durable, deduplicated receipt-email requests; existing rides are unchanged."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_receipt_emails"
down_revision = "0005_test_payments"
branch_labels = depends_on = None


def upgrade():
    op.create_table("receipt_emails",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("ride_id", sa.Uuid(), sa.ForeignKey("rides.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("document_key", sa.String(64), nullable=False),
        sa.Column("recipient", sa.String(254), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(20), server_default="queued", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("ride_id", "user_id", "document_key", name="uq_receipt_emails_document"),
        sa.CheckConstraint("status IN ('queued', 'sent', 'failed')", name="ck_receipt_emails_status"),
        sa.CheckConstraint("attempts BETWEEN 0 AND 3", name="ck_receipt_emails_attempts"))
    op.create_index("ix_receipt_emails_ride_id", "receipt_emails", ["ride_id"])
    op.create_index("ix_receipt_emails_user_id", "receipt_emails", ["user_id"])


def downgrade():
    op.drop_index("ix_receipt_emails_user_id", table_name="receipt_emails")
    op.drop_index("ix_receipt_emails_ride_id", table_name="receipt_emails")
    op.drop_table("receipt_emails")
