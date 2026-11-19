"""Add immutable evidence links to thesis assumptions.

Revision ID: 0013_thesis_evidence_links
Revises: 0012_investment_thesis
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013_thesis_evidence_links"
down_revision = "0012_investment_thesis"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "investment_thesis_evidence_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("thesis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investment_theses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investment_thesis_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assumption_id", sa.String(80), nullable=False),
        sa.Column("evidence_candidate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bq_evidence_candidates.id", ondelete="RESTRICT")),
        sa.Column("metric_result_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("financial_metric_results.id", ondelete="RESTRICT")),
        sa.Column("relationship", sa.String(20), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("(evidence_candidate_id IS NOT NULL AND metric_result_id IS NULL) OR (evidence_candidate_id IS NULL AND metric_result_id IS NOT NULL)", name="ck_thesis_evidence_exactly_one_target"),
        sa.CheckConstraint("relationship IN ('SUPPORTS','CONTRADICTS','QUALIFIES')", name="ck_thesis_evidence_relationship"),
    )
    op.create_index("ix_thesis_evidence_version_assumption", "investment_thesis_evidence_links", ["version_id", "assumption_id"])
    op.execute("""CREATE TRIGGER trg_thesis_evidence_links_immutable BEFORE UPDATE OR DELETE ON investment_thesis_evidence_links FOR EACH ROW EXECUTE FUNCTION reject_thesis_history_mutation()""")

def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_thesis_evidence_links_immutable ON investment_thesis_evidence_links")
    op.drop_index("ix_thesis_evidence_version_assumption", table_name="investment_thesis_evidence_links")
    op.drop_table("investment_thesis_evidence_links")
