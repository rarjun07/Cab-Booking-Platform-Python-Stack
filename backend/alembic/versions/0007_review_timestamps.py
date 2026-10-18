"""Review timestamps and baseline reconciliation of derived rating averages."""
from alembic import op
import sqlalchemy as sa

revision = "0007_review_timestamps"
down_revision = "0006_receipt_emails"
branch_labels = depends_on = None


def upgrade():
    # Existing reviews have unknown dates. Apply the default only after adding
    # the nullable column so old rows are not assigned invented creation times.
    op.add_column("reviews", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("reviews", "created_at", server_default=sa.func.now())
    op.execute("""UPDATE users AS u SET rating_avg = COALESCE(
        (SELECT ROUND(AVG(r.rating), 2) FROM reviews AS r WHERE r.rated_id = u.id), 0)""")


def downgrade():
    op.drop_column("reviews", "created_at")
