"""Persist immutable SEC Company Facts and normalized reported observations.

Revision ID: 0003_sec_financial_data
Revises: 0002_asset_identity
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_sec_financial_data"
down_revision = "0002_asset_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sec_raw_company_facts",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("cik", sa.String(10), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False, server_default="SEC"),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("payload_text", sa.Text(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("connector_version", sa.String(40), nullable=False, server_default="sec-companyfacts-v1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.UniqueConstraint("cik", "payload_hash", name="uq_sec_raw_company_facts_cik_hash"),
    )
    op.create_index("ix_sec_raw_company_facts_cik_retrieved", "sec_raw_company_facts", ["cik", "retrieved_at"])

    op.create_table(
        "financial_facts",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("raw_record_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sec_raw_company_facts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("cik", sa.String(10), nullable=False),
        sa.Column("external_fact_key", sa.String(64), nullable=False),
        sa.Column("metric_id", sa.String(80), nullable=False),
        sa.Column("taxonomy", sa.String(40), nullable=False),
        sa.Column("tag", sa.String(160), nullable=False),
        sa.Column("value", sa.Numeric(38, 10), nullable=False),
        sa.Column("unit", sa.String(40), nullable=False),
        sa.Column("currency", sa.String(3)),
        sa.Column("period_kind", sa.String(20), nullable=False),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("fiscal_year", sa.Integer()),
        sa.Column("fiscal_period", sa.String(8)),
        sa.Column("form", sa.String(20)),
        sa.Column("accession_number", sa.String(30)),
        sa.Column("filed_at", sa.Date()),
        sa.Column("frame", sa.String(40)),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mapping_version", sa.String(40), nullable=False, server_default="sec-us-gaap-v1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.UniqueConstraint("external_fact_key", name="uq_financial_facts_external_key"),
    )
    op.create_index("ix_financial_facts_company_metric_period", "financial_facts", ["company_id", "metric_id", "end_date"])
    op.create_index("ix_financial_facts_cik_filed", "financial_facts", ["cik", "filed_at"])

    op.create_table(
        "normalized_financial_facts",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_fact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("financial_facts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("metric_id", sa.String(80), nullable=False),
        sa.Column("value", sa.Numeric(38, 10), nullable=False),
        sa.Column("unit", sa.String(40), nullable=False),
        sa.Column("currency", sa.String(3)),
        sa.Column("period_kind", sa.String(20), nullable=False),
        sa.Column("fiscal_year", sa.Integer()),
        sa.Column("fiscal_period", sa.String(8)),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("origin", sa.String(20), nullable=False, server_default="REPORTED"),
        sa.Column("derivation_version", sa.String(40)),
        sa.Column("normalized_key", sa.String(64), nullable=False),
        sa.Column("filed_at", sa.Date()),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.UniqueConstraint("normalized_key", name="uq_normalized_financial_facts_key"),
    )
    op.create_index("ix_normalized_facts_company_metric_year", "normalized_financial_facts", ["company_id", "metric_id", "fiscal_year"])

    op.create_table(
        "financial_fact_lineage",
        sa.Column("normalized_fact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("normalized_financial_facts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_fact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("financial_facts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("role", sa.String(30), nullable=False, server_default="DIRECT_SOURCE"),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.UniqueConstraint("normalized_fact_id", "source_fact_id", "role", name="uq_financial_fact_lineage_edge"),
    )

    op.execute("""
        CREATE FUNCTION reject_financial_data_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'financial source and normalized records are append-only';
        END;
        $$ LANGUAGE plpgsql;
    """)
    for table in (
        "sec_raw_company_facts", "financial_facts",
        "normalized_financial_facts", "financial_fact_lineage",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table}_append_only "
            f"BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION reject_financial_data_mutation()"
        )


def downgrade() -> None:
    op.drop_table("financial_fact_lineage")
    op.drop_index("ix_normalized_facts_company_metric_year", table_name="normalized_financial_facts")
    op.drop_table("normalized_financial_facts")
    op.drop_index("ix_financial_facts_cik_filed", table_name="financial_facts")
    op.drop_index("ix_financial_facts_company_metric_period", table_name="financial_facts")
    op.drop_table("financial_facts")
    op.drop_index("ix_sec_raw_company_facts_cik_retrieved", table_name="sec_raw_company_facts")
    op.drop_table("sec_raw_company_facts")
    op.execute("DROP FUNCTION IF EXISTS reject_financial_data_mutation()")
