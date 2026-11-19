"""Add tenant-scoped total-return benchmarks and immutable observations.

Revision ID: 0024_portfolio_benchmarks
Revises: 0023_portfolio_valuations
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0024_portfolio_benchmarks"
down_revision = "0023_portfolio_valuations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_benchmarks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("benchmark_type", sa.String(32), server_default="TOTAL_RETURN_INDEX", nullable=False),
        sa.Column("provider", sa.String(120), nullable=False),
        sa.Column("methodology", sa.String(240), nullable=False),
        sa.Column("source_reference", sa.String(240)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(currency) = 3 AND currency = upper(currency)", name="ck_portfolio_benchmarks_currency"),
        sa.CheckConstraint("benchmark_type = 'TOTAL_RETURN_INDEX'", name="ck_portfolio_benchmarks_type"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "code", name="uq_portfolio_benchmarks_company_code"),
        sa.UniqueConstraint("id", "company_id", name="uq_portfolio_benchmarks_id_company"),
    )
    op.create_index("ix_portfolio_benchmarks_company_active", "portfolio_benchmarks", ["company_id", "is_active"])

    op.create_table(
        "portfolio_benchmark_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("benchmark_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("index_level", sa.Numeric(28, 10), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("source", sa.String(120), nullable=False),
        sa.Column("source_reference", sa.String(240)),
        sa.Column("methodology", sa.String(240), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.CheckConstraint("index_level > 0", name="ck_portfolio_benchmark_index_level_positive"),
        sa.CheckConstraint("length(currency) = 3 AND currency = upper(currency)", name="ck_portfolio_benchmark_observation_currency"),
        sa.ForeignKeyConstraint(
            ["benchmark_id", "company_id"],
            ["portfolio_benchmarks.id", "portfolio_benchmarks.company_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("benchmark_id", "observation_date", name="uq_portfolio_benchmark_observation_date"),
    )
    op.create_index(
        "ix_portfolio_benchmark_observations_company_date",
        "portfolio_benchmark_observations",
        ["company_id", "benchmark_id", "observation_date"],
    )
    op.execute("""
        CREATE FUNCTION prevent_portfolio_benchmark_observation_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'portfolio_benchmark_observations is append-only; % is not permitted', TG_OP
                USING ERRCODE = '55000';
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_portfolio_benchmark_observations_immutable
        BEFORE UPDATE OR DELETE ON portfolio_benchmark_observations
        FOR EACH ROW EXECUTE FUNCTION prevent_portfolio_benchmark_observation_mutation();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_portfolio_benchmark_observations_immutable ON portfolio_benchmark_observations")
    op.execute("DROP FUNCTION IF EXISTS prevent_portfolio_benchmark_observation_mutation()")
    op.drop_index("ix_portfolio_benchmark_observations_company_date", table_name="portfolio_benchmark_observations")
    op.drop_table("portfolio_benchmark_observations")
    op.drop_index("ix_portfolio_benchmarks_company_active", table_name="portfolio_benchmarks")
    op.drop_table("portfolio_benchmarks")
