from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.database.base import Base, UUIDPrimaryKeyMixin


class BQSourceDocument(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "bq_source_documents"
    __table_args__ = (UniqueConstraint("company_id", "accession_number", "document_hash"), Index("ix_bq_source_documents_company_filed", "company_id", "filed_at"))
    company_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    accession_number: Mapped[str] = mapped_column(String(32), nullable=False)
    form_type: Mapped[str] = mapped_column(String(12), nullable=False)
    filed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    document_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    original_content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    extraction_version: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class BQDocumentSection(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "bq_document_sections"
    __table_args__ = (UniqueConstraint("document_id", "section_key", "sequence_number"), Index("ix_bq_document_sections_document", "document_id"))
    document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("bq_source_documents.id", ondelete="RESTRICT"), nullable=False)
    section_key: Mapped[str] = mapped_column(String(80), nullable=False)
    heading: Mapped[str] = mapped_column(String(500), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class BQEvidenceCandidate(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "bq_evidence_candidates"
    __table_args__ = (Index("ix_bq_evidence_candidates_company_status", "company_id", "status"),)
    company_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("bq_source_documents.id", ondelete="RESTRICT"), nullable=False)
    section_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("bq_document_sections.id", ondelete="RESTRICT"))
    criterion_key: Mapped[str] = mapped_column(String(100), nullable=False)
    passage: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    source_locator: Mapped[str] = mapped_column(String(500), nullable=False)
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    review_comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
