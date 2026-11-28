"""Persist verified SEC SIC issuer classification.

Revision ID: 0025_sec_sic_classification
Revises: 0024_portfolio_benchmarks
"""
from alembic import op
import sqlalchemy as sa

revision = "0025_sec_sic_classification"
down_revision = "0024_portfolio_benchmarks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("sic_code", sa.String(4), nullable=True))
    op.add_column("companies", sa.Column("sic_description", sa.String(256), nullable=True))
    op.add_column("companies", sa.Column("sic_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        "ck_companies_sic_code_format",
        "companies",
        "sic_code IS NULL OR sic_code ~ '^[0-9]{4}$'",
    )
    op.create_index("ix_companies_sic_code", "companies", ["sic_code"])


def downgrade() -> None:
    op.drop_index("ix_companies_sic_code", table_name="companies")
    op.drop_constraint("ck_companies_sic_code_format", "companies", type_="check")
    op.drop_column("companies", "sic_verified_at")
    op.drop_column("companies", "sic_description")
    op.drop_column("companies", "sic_code")
