"""Add tenant-scoped portfolio containers and immutable transaction ledger.

Revision ID: 0022_portfolio_transaction_ledger
Revises: 0021_valuation_run_immutability
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0022_portfolio_transaction_ledger"
down_revision = "0021_valuation_run_immutability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolios",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('ACTIVE','ARCHIVED')", name="ck_portfolios_status"),
        sa.CheckConstraint("base_currency ~ '^[A-Z]{3}$'", name="ck_portfolios_currency"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "company_id", name="uq_portfolios_id_company"),
    )
    op.create_index(
        "ix_portfolios_company_status_updated", "portfolios",
        ["company_id", "status", "updated_at"],
    )

    op.create_table(
        "portfolio_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("transaction_type", sa.String(length=20), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("settlement_date", sa.Date(), nullable=True),
        sa.Column("quantity", sa.Numeric(28, 10), nullable=True),
        sa.Column("unit_price", sa.Numeric(28, 10), nullable=True),
        sa.Column("gross_amount", sa.Numeric(28, 10), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("fees", sa.Numeric(28, 10), server_default="0", nullable=False),
        sa.Column("taxes", sa.Numeric(28, 10), server_default="0", nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("external_reference", sa.String(length=160), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "transaction_type IN ('BUY','SELL','DIVIDEND','DEPOSIT','WITHDRAWAL','FEE','TAX','INTEREST')",
            name="ck_portfolio_transactions_type",
        ),
        sa.CheckConstraint("gross_amount > 0", name="ck_portfolio_transactions_gross_positive"),
        sa.CheckConstraint("quantity IS NULL OR quantity > 0", name="ck_portfolio_transactions_quantity_positive"),
        sa.CheckConstraint("unit_price IS NULL OR unit_price > 0", name="ck_portfolio_transactions_unit_price_positive"),
        sa.CheckConstraint("fees >= 0 AND taxes >= 0", name="ck_portfolio_transactions_costs_nonnegative"),
        sa.CheckConstraint(
            "settlement_date IS NULL OR settlement_date >= trade_date",
            name="ck_portfolio_transactions_settlement_date",
        ),
        sa.CheckConstraint(
            "((transaction_type IN ('BUY','SELL')) AND asset_id IS NOT NULL AND quantity IS NOT NULL "
            "AND unit_price IS NOT NULL AND gross_amount = quantity * unit_price) OR "
            "(transaction_type = 'DIVIDEND' AND asset_id IS NOT NULL AND quantity IS NULL AND unit_price IS NULL) OR "
            "(transaction_type = 'INTEREST' AND asset_id IS NULL AND quantity IS NULL AND unit_price IS NULL) OR "
            "(transaction_type IN ('DEPOSIT','WITHDRAWAL') AND asset_id IS NULL AND quantity IS NULL AND unit_price IS NULL) OR "
            "(transaction_type IN ('FEE','TAX') AND quantity IS NULL AND unit_price IS NULL)",
            name="ck_portfolio_transactions_shape",
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id", "company_id"], ["portfolios.id", "portfolios.company_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("portfolio_id", "idempotency_key", name="uq_portfolio_transaction_idempotency"),
    )
    op.create_index(
        "ix_portfolio_transactions_portfolio_trade_recorded", "portfolio_transactions",
        ["portfolio_id", "trade_date", "recorded_at"],
    )
    op.create_index(
        "ix_portfolio_transactions_asset_trade", "portfolio_transactions",
        ["asset_id", "trade_date"],
    )
    op.execute(
        """
        CREATE FUNCTION prevent_portfolio_transaction_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION
                'portfolio_transactions is append-only; % is not permitted', TG_OP
                USING ERRCODE = '55000';
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_portfolio_transactions_immutable
        BEFORE UPDATE OR DELETE ON portfolio_transactions
        FOR EACH ROW
        EXECUTE FUNCTION prevent_portfolio_transaction_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_portfolio_transactions_immutable ON portfolio_transactions")
    op.execute("DROP FUNCTION IF EXISTS prevent_portfolio_transaction_mutation()")
    op.drop_index("ix_portfolio_transactions_asset_trade", table_name="portfolio_transactions")
    op.drop_index("ix_portfolio_transactions_portfolio_trade_recorded", table_name="portfolio_transactions")
    op.drop_table("portfolio_transactions")
    op.drop_index("ix_portfolios_company_status_updated", table_name="portfolios")
    op.drop_table("portfolios")
