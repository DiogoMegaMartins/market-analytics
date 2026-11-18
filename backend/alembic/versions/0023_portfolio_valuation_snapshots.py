"""Add immutable, dated portfolio valuation snapshots.

Revision ID: 0023_portfolio_valuations
Revises: 0022_portfolio_ledger
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0023_portfolio_valuations"
down_revision = "0022_portfolio_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_valuation_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("valuation_date", sa.Date(), nullable=False),
        sa.Column("market_value", sa.Numeric(28, 10), nullable=False),
        sa.Column("cash_value", sa.Numeric(28, 10), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("valuation_source", sa.String(32), nullable=False),
        sa.Column("methodology", sa.String(160), nullable=False),
        sa.Column("source_reference", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("market_value >= 0 AND cash_value >= 0", name="ck_portfolio_valuation_values_nonnegative"),
        sa.CheckConstraint("length(currency) = 3 AND currency = upper(currency)", name="ck_portfolio_valuation_currency"),
        sa.CheckConstraint("length(idempotency_key) > 0", name="ck_portfolio_valuation_idempotency_nonempty"),
        sa.CheckConstraint("valuation_source IN ('MANUAL','BROKER_STATEMENT','DATA_PROVIDER')", name="ck_portfolio_valuation_source"),
        sa.ForeignKeyConstraint(["portfolio_id", "company_id"], ["portfolios.id", "portfolios.company_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("portfolio_id", "idempotency_key", name="uq_portfolio_valuation_idempotency"),
    )
    op.create_index("ix_portfolio_valuation_portfolio_date", "portfolio_valuation_snapshots", ["portfolio_id", "valuation_date", "recorded_at"])
    op.execute("""
        CREATE FUNCTION prevent_portfolio_valuation_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'portfolio_valuation_snapshots is append-only; % is not permitted', TG_OP
                USING ERRCODE = '55000';
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_portfolio_valuation_snapshots_immutable
        BEFORE UPDATE OR DELETE ON portfolio_valuation_snapshots
        FOR EACH ROW EXECUTE FUNCTION prevent_portfolio_valuation_mutation();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_portfolio_valuation_snapshots_immutable ON portfolio_valuation_snapshots")
    op.execute("DROP FUNCTION IF EXISTS prevent_portfolio_valuation_mutation()")
    op.drop_index("ix_portfolio_valuation_portfolio_date", table_name="portfolio_valuation_snapshots")
    op.drop_table("portfolio_valuation_snapshots")
