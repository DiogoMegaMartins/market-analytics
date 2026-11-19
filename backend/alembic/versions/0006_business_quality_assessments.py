"""Persist immutable Business Quality assessments.

Revision ID: 0006_bq_assessments
Revises: 0005_sec_provider_cache
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_bq_assessments"
down_revision = "0005_sec_provider_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_quality_assessments",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("engine_version", sa.String(40), nullable=False),
        sa.Column("rubric_version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("overall_score", sa.Numeric(6, 2)),
        sa.Column("classification", sa.String(30), nullable=False),
        sa.Column("completeness_pct", sa.Numeric(6, 2), nullable=False),
        sa.Column("analysis_confidence", sa.String(20), nullable=False),
        sa.Column("observations", postgresql.JSONB(), nullable=False),
        sa.Column("results", postgresql.JSONB(), nullable=False),
        sa.Column("analyst_id", sa.String(120)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    )
    op.create_index("ix_bq_assessments_company_created", "business_quality_assessments", ["company_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_bq_assessments_company_created", table_name="business_quality_assessments")
    op.drop_table("business_quality_assessments")
