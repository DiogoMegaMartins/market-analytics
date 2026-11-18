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



class PortfolioValuationSnapshot(UUIDPrimaryKeyMixin, Base):
    """Immutable, dated portfolio valuation input for future performance calculations."""

    __tablename__ = "portfolio_valuation_snapshots"
    __table_args__ = (
        ForeignKeyConstraint(["portfolio_id", "company_id"], ["portfolios.id", "portfolios.company_id"], ondelete="RESTRICT"),
        UniqueConstraint("portfolio_id", "idempotency_key", name="uq_portfolio_valuation_idempotency"),
        CheckConstraint("market_value >= 0 AND cash_value >= 0", name="ck_portfolio_valuation_values_nonnegative"),
        CheckConstraint("length(currency) = 3 AND currency = upper(currency)", name="ck_portfolio_valuation_currency"),
        CheckConstraint("length(idempotency_key) > 0", name="ck_portfolio_valuation_idempotency_nonempty"),
        CheckConstraint("valuation_source IN ('MANUAL','BROKER_STATEMENT','DATA_PROVIDER')", name="ck_portfolio_valuation_source"),
        Index("ix_portfolio_valuation_portfolio_date", "portfolio_id", "valuation_date", "recorded_at"),
    )
    portfolio_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    company_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    valuation_date: Mapped[date] = mapped_column(Date, nullable=False)
    market_value: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False)
    cash_value: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    valuation_source: Mapped[str] = mapped_column(String(32), nullable=False)
    methodology: Mapped[str] = mapped_column(String(160), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
