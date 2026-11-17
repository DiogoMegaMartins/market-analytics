from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database.base import Base, UUIDPrimaryKeyMixin


class InvestmentThesisEvidenceLink(UUIDPrimaryKeyMixin, Base):
    """Immutable, company-scoped link from one thesis assumption to one persisted source."""
    __tablename__ = "investment_thesis_evidence_links"
    __table_args__ = (
        CheckConstraint("(evidence_candidate_id IS NOT NULL AND metric_result_id IS NULL) OR (evidence_candidate_id IS NULL AND metric_result_id IS NOT NULL)", name="ck_thesis_evidence_exactly_one_target"),
        CheckConstraint("relationship IN ('SUPPORTS','CONTRADICTS','QUALIFIES')", name="ck_thesis_evidence_relationship"),
        Index("ix_thesis_evidence_version_assumption", "version_id", "assumption_id"),
    )
    thesis_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("investment_theses.id", ondelete="RESTRICT"), nullable=False)
    version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("investment_thesis_versions.id", ondelete="RESTRICT"), nullable=False)
    assumption_id: Mapped[str] = mapped_column(String(80), nullable=False)
    evidence_candidate_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("bq_evidence_candidates.id", ondelete="RESTRICT"))
    metric_result_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("financial_metric_results.id", ondelete="RESTRICT"))
    relationship: Mapped[str] = mapped_column(String(20), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
