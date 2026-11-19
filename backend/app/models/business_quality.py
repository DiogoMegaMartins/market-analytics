from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database.base import Base, UUIDPrimaryKeyMixin


class BusinessQualityAssessment(UUIDPrimaryKeyMixin, Base):
    """Immutable, versioned Business Quality assessment and its full audit payload."""
    __tablename__ = "business_quality_assessments"
    __table_args__ = (Index("ix_bq_assessments_company_created", "company_id", "created_at"),)

    company_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(40), nullable=False)
    rubric_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    overall_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    classification: Mapped[str] = mapped_column(String(30), nullable=False)
    completeness_pct: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    analysis_confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    observations: Mapped[dict] = mapped_column(JSONB, nullable=False)
    results: Mapped[dict] = mapped_column(JSONB, nullable=False)
    analyst_id: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
