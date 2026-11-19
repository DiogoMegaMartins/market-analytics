from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database.base import Base, UUIDPrimaryKeyMixin


class InvestmentThesisAlert(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "investment_thesis_alerts"
    __table_args__ = (
        UniqueConstraint("thesis_id", "version_id", "assumption_id", "metric_run_id", "alert_type", name="uq_thesis_alert_detection"),
        Index("ix_thesis_alerts_thesis_status_created", "thesis_id", "status", "created_at"),
        CheckConstraint("status IN ('PENDING','REVIEWED','RESOLVED')", name="ck_thesis_alert_status"),
        CheckConstraint("alert_type IN ('THRESHOLD_BREACH','MATERIAL_CHANGE')", name="ck_thesis_alert_type"),
    )

    thesis_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("investment_theses.id", ondelete="RESTRICT"), nullable=False)
    version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("investment_thesis_versions.id", ondelete="RESTRICT"), nullable=False)
    assumption_id: Mapped[str] = mapped_column(String(80), nullable=False)
    metric_run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("financial_metric_runs.id", ondelete="RESTRICT"), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", server_default="PENDING")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InvestmentThesisAlertEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "investment_thesis_alert_events"
    __table_args__ = (Index("ix_thesis_alert_events_alert_created", "alert_id", "created_at"),
                      CheckConstraint("to_status IN ('PENDING','REVIEWED','RESOLVED')", name="ck_thesis_alert_event_to_status"))

    alert_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("investment_thesis_alerts.id", ondelete="RESTRICT"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
