from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database.base import Base, UUIDPrimaryKeyMixin


class BQEvidenceReviewEvent(UUIDPrimaryKeyMixin, Base):
    """Append-only evidence review event; hash-linked to the preceding event."""
    __tablename__ = "bq_evidence_review_events"
    __table_args__ = (Index("ix_bq_evidence_review_events_candidate_created", "candidate_id", "created_at"),)

    candidate_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("bq_evidence_candidates.id", ondelete="RESTRICT"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    previous_event_hash: Mapped[str | None] = mapped_column(String(64))
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BQAssessmentEvidenceLink(UUIDPrimaryKeyMixin, Base):
    """Immutable point-in-time eligibility decision for evidence used by an assessment."""
    __tablename__ = "bq_assessment_evidence_links"
    __table_args__ = (UniqueConstraint("assessment_id", "candidate_id", name="uq_bq_assessment_evidence_link"),
                      Index("ix_bq_assessment_evidence_assessment", "assessment_id"))

    assessment_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("business_quality_assessments.id", ondelete="RESTRICT"), nullable=False)
    candidate_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("bq_evidence_candidates.id", ondelete="RESTRICT"), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    eligible: Mapped[bool] = mapped_column(nullable=False)
    decision_reason: Mapped[str] = mapped_column(String(60), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
