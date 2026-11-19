from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database.base import Base, UUIDPrimaryKeyMixin


class BusinessQualityReviewEvent(UUIDPrimaryKeyMixin, Base):
    """Append-only workflow event for an immutable Business Quality assessment."""
    __tablename__ = "business_quality_review_events"
    __table_args__ = (Index("ix_bq_review_events_assessment_created", "assessment_id", "created_at"),)

    assessment_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("business_quality_assessments.id", ondelete="RESTRICT"), nullable=False)
    from_status: Mapped[str] = mapped_column(String(20), nullable=False)
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
