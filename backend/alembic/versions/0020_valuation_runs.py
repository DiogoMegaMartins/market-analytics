"""Persist versioned FCFF DCF valuation runs.

Revision ID: 0020_valuation_runs
Revises: 0019_neon_operational_indexes
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0020_valuation_runs"
down_revision = "0019_neon_operational_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "valuation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("valuation_version", sa.String(length=40), nullable=False),
        sa.Column("method", sa.String(length=30), nullable=False),
        sa.Column("base_year", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("assumptions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_valuation_runs_company_created", "valuation_runs", ["company_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_valuation_runs_company_created", table_name="valuation_runs")
    op.drop_table("valuation_runs")
