"""Append-only evidence review audit and point-in-time assessment links.

Revision ID: 0009_bq_evidence_audit_pit
Revises: 0008_business_quality_evidence
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_bq_evidence_audit_pit"
down_revision = "0008_business_quality_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bq_evidence_review_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bq_evidence_candidates.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("from_status", sa.String(20)), sa.Column("to_status", sa.String(20), nullable=False),
        sa.Column("actor_id", sa.String(120), nullable=False), sa.Column("comment", sa.Text()),
        sa.Column("previous_event_hash", sa.String(64)), sa.Column("event_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_bq_evidence_review_events_candidate_created", "bq_evidence_review_events", ["candidate_id", "created_at"])
    op.create_table(
        "bq_assessment_evidence_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("business_quality_assessments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bq_evidence_candidates.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False), sa.Column("eligible", sa.Boolean(), nullable=False),
        sa.Column("decision_reason", sa.String(60), nullable=False), sa.Column("policy_version", sa.String(40), nullable=False),
        sa.Column("evidence_hash", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("assessment_id", "candidate_id", name="uq_bq_assessment_evidence_link"),
    )
    op.create_index("ix_bq_assessment_evidence_assessment", "bq_assessment_evidence_links", ["assessment_id"])


def downgrade() -> None:
    op.drop_table("bq_assessment_evidence_links")
    op.drop_table("bq_evidence_review_events")
