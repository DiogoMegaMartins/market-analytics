"""Append-only Business Quality review workflow events.

Revision ID: 0007_bq_review_events
Revises: 0006_bq_assessments
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_bq_review_events"
down_revision = "0006_bq_assessments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_quality_review_events",
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("business_quality_assessments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("from_status", sa.String(20), nullable=False),
        sa.Column("to_status", sa.String(20), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("actor_id", sa.String(120), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    )
    op.create_index("ix_bq_review_events_assessment_created", "business_quality_review_events", ["assessment_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_bq_review_events_assessment_created", table_name="business_quality_review_events")
    op.drop_table("business_quality_review_events")
