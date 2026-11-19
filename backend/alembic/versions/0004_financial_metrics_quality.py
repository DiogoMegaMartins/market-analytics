"""Persist versioned financial metric runs, results, lineage and quality findings.

Revision ID: 0004_financial_metrics_quality
Revises: 0003_sec_financial_data
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_financial_metrics_quality"
down_revision = "0003_sec_financial_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "financial_metric_runs",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("resolution_policy", sa.String(30), nullable=False),
        sa.Column("as_known_at", sa.Date()),
        sa.Column("engine_version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    )
    op.create_index("ix_metric_runs_company_created", "financial_metric_runs", ["company_id", "created_at"])
    op.create_table(
        "financial_metric_results",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("financial_metric_runs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("metric_id", sa.String(80), nullable=False),
        sa.Column("value", sa.Numeric(38, 16)),
        sa.Column("unit", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.UniqueConstraint("run_id", "metric_id", name="uq_metric_result_run_metric"),
    )
    op.create_index("ix_metric_results_company_year", "financial_metric_results", ["company_id", "fiscal_year"])
    op.create_table(
        "financial_metric_lineage",
        sa.Column("result_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("financial_metric_results.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("normalized_fact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("normalized_financial_facts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.UniqueConstraint("result_id", "normalized_fact_id", name="uq_metric_lineage_result_fact"),
    )
    op.create_table(
        "financial_quality_findings",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("financial_metric_runs.id", ondelete="RESTRICT")),
        sa.Column("rule_id", sa.String(80), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metric_id", sa.String(80)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    )
    op.create_index("ix_fin_quality_company_year", "financial_quality_findings", ["company_id", "fiscal_year"])
    for table in ("financial_metric_runs", "financial_metric_results", "financial_metric_lineage", "financial_quality_findings"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_append_only "
            f"BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION reject_financial_data_mutation()"
        )


def downgrade() -> None:
    op.drop_index("ix_fin_quality_company_year", table_name="financial_quality_findings")
    op.drop_table("financial_quality_findings")
    op.drop_table("financial_metric_lineage")
    op.drop_index("ix_metric_results_company_year", table_name="financial_metric_results")
    op.drop_table("financial_metric_results")
    op.drop_index("ix_metric_runs_company_created", table_name="financial_metric_runs")
    op.drop_table("financial_metric_runs")
