from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint,
    Index, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database.base import Base, UUIDPrimaryKeyMixin


class PortfolioBenchmark(UUIDPrimaryKeyMixin, Base):
    """Tenant-owned benchmark definition; levels must represent total return."""

    __tablename__ = "portfolio_benchmarks"
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_portfolio_benchmarks_company_code"),
        UniqueConstraint("id", "company_id", name="uq_portfolio_benchmarks_id_company"),
        CheckConstraint("length(currency) = 3 AND currency = upper(currency)", name="ck_portfolio_benchmarks_currency"),
        CheckConstraint("benchmark_type = 'TOTAL_RETURN_INDEX'", name="ck_portfolio_benchmarks_type"),
        Index("ix_portfolio_benchmarks_company_active", "company_id", "is_active"),
    )

    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    benchmark_type: Mapped[str] = mapped_column(String(32), nullable=False, default="TOTAL_RETURN_INDEX")
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    methodology: Mapped[str] = mapped_column(String(240), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(240))
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PortfolioBenchmarkObservation(UUIDPrimaryKeyMixin, Base):
    """Append-only, source-attributed total-return index level for one date."""

    __tablename__ = "portfolio_benchmark_observations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["benchmark_id", "company_id"],
            ["portfolio_benchmarks.id", "portfolio_benchmarks.company_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("benchmark_id", "observation_date", name="uq_portfolio_benchmark_observation_date"),
        CheckConstraint("index_level > 0", name="ck_portfolio_benchmark_index_level_positive"),
        CheckConstraint("length(currency) = 3 AND currency = upper(currency)", name="ck_portfolio_benchmark_observation_currency"),
        Index("ix_portfolio_benchmark_observations_company_date", "company_id", "benchmark_id", "observation_date"),
    )

    benchmark_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    company_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    index_level: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(240))
    methodology: Mapped[str] = mapped_column(String(240), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
