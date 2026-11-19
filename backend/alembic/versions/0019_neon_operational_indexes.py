"""Neon indexes for point-in-time financial queries; no source rows are changed."""
from alembic import op
revision = "0019_neon_operational_indexes"
down_revision = "0018_point_in_time_contract"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.create_index("ix_financial_facts_company_metric_filed_accession", "financial_facts", ["company_id", "metric_id", "end_date", "filed_at", "accession_number"])
    op.create_index("ix_normalized_facts_company_metric_available", "normalized_financial_facts", ["company_id", "metric_id", "end_date", "available_at"])
def downgrade() -> None:
    op.drop_index("ix_normalized_facts_company_metric_available", table_name="normalized_financial_facts")
    op.drop_index("ix_financial_facts_company_metric_filed_accession", table_name="financial_facts")
