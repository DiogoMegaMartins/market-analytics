from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SECRawCompanyFacts(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sec_raw_company_facts"
    __table_args__ = (
        UniqueConstraint("cik", "payload_hash", name="uq_sec_raw_company_facts_cik_hash"),
        Index("ix_sec_raw_company_facts_cik_retrieved", "cik", "retrieved_at"),
    )

    company_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    cik: Mapped[str] = mapped_column(String(10), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False, default="SEC", server_default="SEC")
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_text: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    connector_version: Mapped[str] = mapped_column(String(40), nullable=False, default="sec-companyfacts-v1", server_default="sec-companyfacts-v1")


class FinancialFact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "financial_facts"
    __table_args__ = (
        UniqueConstraint("external_fact_key", name="uq_financial_facts_external_key"),
        Index("ix_financial_facts_company_metric_period", "company_id", "metric_id", "end_date"),
        Index("ix_financial_facts_cik_filed", "cik", "filed_at"),
    )

    company_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    raw_record_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("sec_raw_company_facts.id", ondelete="RESTRICT"), nullable=False)
    cik: Mapped[str] = mapped_column(String(10), nullable=False)
    external_fact_key: Mapped[str] = mapped_column(String(64), nullable=False)
    metric_id: Mapped[str] = mapped_column(String(80), nullable=False)
    taxonomy: Mapped[str] = mapped_column(String(40), nullable=False)
    tag: Mapped[str] = mapped_column(String(160), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(38, 10), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(3))
    period_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[int | None] = mapped_column(Integer)
    fiscal_period: Mapped[str | None] = mapped_column(String(8))
    form: Mapped[str | None] = mapped_column(String(20))
    accession_number: Mapped[str | None] = mapped_column(String(30))
    filed_at: Mapped[date | None] = mapped_column(Date)
    frame: Mapped[str | None] = mapped_column(String(40))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    mapping_version: Mapped[str] = mapped_column(String(40), nullable=False, default="sec-us-gaap-v1", server_default="sec-us-gaap-v1")


class NormalizedFinancialFact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "normalized_financial_facts"
    __table_args__ = (
        UniqueConstraint("normalized_key", name="uq_normalized_financial_facts_key"),
        Index("ix_normalized_facts_company_metric_year", "company_id", "metric_id", "fiscal_year"),
    )

    company_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    source_fact_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("financial_facts.id", ondelete="RESTRICT"), nullable=False)
    metric_id: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(38, 10), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(3))
    period_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    fiscal_year: Mapped[int | None] = mapped_column(Integer)
    fiscal_period: Mapped[str | None] = mapped_column(String(8))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    origin: Mapped[str] = mapped_column(String(20), nullable=False, default="REPORTED", server_default="REPORTED")
    derivation_version: Mapped[str | None] = mapped_column(String(40))
    normalized_key: Mapped[str] = mapped_column(String(64), nullable=False)
    filed_at: Mapped[date | None] = mapped_column(Date)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    lineage: Mapped[list["FinancialFactLineage"]] = relationship(back_populates="normalized_fact")


class FinancialFactLineage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "financial_fact_lineage"
    __table_args__ = (UniqueConstraint("normalized_fact_id", "source_fact_id", "role", name="uq_financial_fact_lineage_edge"),)

    normalized_fact_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("normalized_financial_facts.id", ondelete="RESTRICT"), nullable=False)
    source_fact_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("financial_facts.id", ondelete="RESTRICT"), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="DIRECT_SOURCE", server_default="DIRECT_SOURCE")
    normalized_fact: Mapped[NormalizedFinancialFact] = relationship(back_populates="lineage")


class FinancialMetricRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "financial_metric_runs"
    __table_args__ = (Index("ix_metric_runs_company_created", "company_id", "created_at"),)

    company_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    resolution_policy: Mapped[str] = mapped_column(String(30), nullable=False)
    as_known_at: Mapped[date | None] = mapped_column(Date)
    engine_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FinancialMetricResult(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "financial_metric_results"
    __table_args__ = (
        UniqueConstraint("run_id", "metric_id", name="uq_metric_result_run_metric"),
        Index("ix_metric_results_company_year", "company_id", "fiscal_year"),
    )

    run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("financial_metric_runs.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    metric_id: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(38, 16))
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)


class FinancialMetricLineage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "financial_metric_lineage"
    __table_args__ = (UniqueConstraint("result_id", "normalized_fact_id", name="uq_metric_lineage_result_fact"),)

    result_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("financial_metric_results.id", ondelete="RESTRICT"), nullable=False)
    normalized_fact_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("normalized_financial_facts.id", ondelete="RESTRICT"), nullable=False)


class FinancialQualityFinding(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "financial_quality_findings"
    __table_args__ = (Index("ix_fin_quality_company_year", "company_id", "fiscal_year"),)

    company_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    run_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("financial_metric_runs.id", ondelete="RESTRICT"))
    rule_id: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metric_id: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SECProviderCache(UUIDPrimaryKeyMixin, Base):
    """Mutable cache of provider responses; raw filing payloads remain immutable elsewhere."""
    __tablename__ = "sec_provider_cache"
    __table_args__ = (
        UniqueConstraint("provider", "cache_key", name="uq_sec_provider_cache_provider_key"),
        Index("ix_sec_provider_cache_expires", "expires_at"),
    )

    provider: Mapped[str] = mapped_column(String(30), nullable=False, default="SEC", server_default="SEC")
    cache_key: Mapped[str] = mapped_column(String(300), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_text: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ValuationRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "valuation_runs"
    __table_args__ = (
        Index("ix_valuation_runs_company_created", "company_id", "created_at"),
    )

    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    valuation_version: Mapped[str] = mapped_column(String(40), nullable=False)
    method: Mapped[str] = mapped_column(String(30), nullable=False)
    base_year: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    assumptions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
