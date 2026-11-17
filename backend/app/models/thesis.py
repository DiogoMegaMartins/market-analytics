from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database.base import Base, UUIDPrimaryKeyMixin


class InvestmentThesis(UUIDPrimaryKeyMixin, Base):
    """Personal thesis workspace attached to a company."""
    __tablename__ = "investment_theses"
    __table_args__ = (
        Index("ix_investment_theses_company_owner", "company_id", "owner_user_id", "updated_at"),
    )

    company_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    owner_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", server_default="ACTIVE")
    current_version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InvestmentThesisVersion(UUIDPrimaryKeyMixin, Base):
    """Immutable thesis content and explicit, machine-checkable assumptions."""
    __tablename__ = "investment_thesis_versions"
    __table_args__ = (
        UniqueConstraint("thesis_id", "version_number", name="uq_thesis_version_number"),
        Index("ix_thesis_versions_created", "thesis_id", "created_at"),
    )

    thesis_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("investment_theses.id", ondelete="RESTRICT"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    assumptions: Mapped[list] = mapped_column(JSONB, nullable=False)
    risks: Mapped[list] = mapped_column(JSONB, nullable=False)
    evidence_references: Mapped[list] = mapped_column(JSONB, nullable=False)
    author_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InvestmentThesisEvent(UUIDPrimaryKeyMixin, Base):
    """Append-only evaluation and analyst decision history."""
    __tablename__ = "investment_thesis_events"
    __table_args__ = (
        Index("ix_thesis_events_thesis_created", "thesis_id", "created_at"),
    )

    thesis_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("investment_theses.id", ondelete="RESTRICT"), nullable=False)
    version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("investment_thesis_versions.id", ondelete="RESTRICT"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
