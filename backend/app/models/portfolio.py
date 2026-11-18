from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database.base import Base, UUIDPrimaryKeyMixin


class Portfolio(UUIDPrimaryKeyMixin, Base):
    """Tenant-owned portfolio container; positions are derived from its ledger."""

    __tablename__ = "portfolios"
    __table_args__ = (
        UniqueConstraint("id", "company_id", name="uq_portfolios_id_company"),
        Index("ix_portfolios_company_status_updated", "company_id", "status", "updated_at"),
        CheckConstraint("status IN ('ACTIVE','ARCHIVED')", name="ck_portfolios_status"),
        CheckConstraint("base_currency ~ '^[A-Z]{3}$'", name="ck_portfolios_currency"),
    )

    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE", server_default="ACTIVE")
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PortfolioTransaction(UUIDPrimaryKeyMixin, Base):
    """Append-only transaction fact; holdings and performance are derived later."""

    __tablename__ = "portfolio_transactions"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "idempotency_key", name="uq_portfolio_transaction_idempotency"),
        ForeignKeyConstraint(
            ["portfolio_id", "company_id"], ["portfolios.id", "portfolios.company_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="ck_portfolio_transactions_currency"),
        CheckConstraint("length(idempotency_key) > 0", name="ck_portfolio_transactions_idempotency_nonempty"),
        Index("ix_portfolio_transactions_portfolio_trade_recorded", "portfolio_id", "trade_date", "recorded_at"),
        Index("ix_portfolio_transactions_asset_trade", "asset_id", "trade_date"),
        CheckConstraint(
            "transaction_type IN ('BUY','SELL','DIVIDEND','DEPOSIT','WITHDRAWAL','FEE','TAX','INTEREST')",
            name="ck_portfolio_transactions_type",
        ),
        CheckConstraint("gross_amount > 0", name="ck_portfolio_transactions_gross_positive"),
        CheckConstraint("quantity IS NULL OR quantity > 0", name="ck_portfolio_transactions_quantity_positive"),
        CheckConstraint("unit_price IS NULL OR unit_price > 0", name="ck_portfolio_transactions_unit_price_positive"),
        CheckConstraint("fees >= 0 AND taxes >= 0", name="ck_portfolio_transactions_costs_nonnegative"),
        CheckConstraint("settlement_date IS NULL OR settlement_date >= trade_date", name="ck_portfolio_transactions_settlement_date"),
        CheckConstraint(
            "((transaction_type IN ('BUY','SELL')) AND asset_id IS NOT NULL AND quantity IS NOT NULL "
            "AND unit_price IS NOT NULL AND gross_amount = quantity * unit_price) OR "
            "(transaction_type = 'DIVIDEND' AND asset_id IS NOT NULL AND quantity IS NULL AND unit_price IS NULL) OR "
            "(transaction_type = 'INTEREST' AND asset_id IS NULL AND quantity IS NULL AND unit_price IS NULL) OR "
            "(transaction_type IN ('DEPOSIT','WITHDRAWAL') AND asset_id IS NULL AND quantity IS NULL AND unit_price IS NULL) OR "
            "(transaction_type IN ('FEE','TAX') AND quantity IS NULL AND unit_price IS NULL)",
            name="ck_portfolio_transactions_shape",
        ),
    )

    portfolio_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    company_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    asset_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("assets.id", ondelete="RESTRICT")
    )
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    settlement_date: Mapped[date | None] = mapped_column(Date)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(28, 10))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(28, 10))
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    fees: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False, default=Decimal("0"))
    taxes: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False, default=Decimal("0"))
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(160))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
