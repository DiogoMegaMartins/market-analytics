"""Persist source documents, extracted sections and reviewable evidence candidates.

Revision ID: 0008_business_quality_evidence
Revises: 0007_bq_review_events
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = "0008_business_quality_evidence"
down_revision = "0007_bq_review_events"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("bq_source_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("accession_number", sa.String(32), nullable=False), sa.Column("form_type", sa.String(12), nullable=False),
        sa.Column("filed_at", sa.DateTime(timezone=True), nullable=False), sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("source_url", sa.Text(), nullable=False), sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("document_hash", sa.String(64), nullable=False), sa.Column("original_content", sa.LargeBinary(), nullable=False),
        sa.Column("extraction_version", sa.String(40), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("company_id", "accession_number", "document_hash", name="uq_bq_source_document_identity"))
    op.create_index("ix_bq_source_documents_company_filed", "bq_source_documents", ["company_id", "filed_at"])
    op.create_table("bq_document_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bq_source_documents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("section_key", sa.String(80), nullable=False), sa.Column("heading", sa.String(500), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False), sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False), sa.Column("extraction_method", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_id", "section_key", "sequence_number", name="uq_bq_section_sequence"))
    op.create_index("ix_bq_document_sections_document", "bq_document_sections", ["document_id"])
    op.create_table("bq_evidence_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bq_source_documents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bq_document_sections.id", ondelete="RESTRICT")),
        sa.Column("criterion_key", sa.String(100), nullable=False), sa.Column("passage", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False), sa.Column("status", sa.String(20), nullable=False),
        sa.Column("source_locator", sa.String(500), nullable=False), sa.Column("evidence_hash", sa.String(64), nullable=False),
        sa.Column("created_by", sa.String(120), nullable=False), sa.Column("reviewed_by", sa.String(120)),
        sa.Column("review_comment", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_bq_evidence_candidates_company_status", "bq_evidence_candidates", ["company_id", "status"])

def downgrade() -> None:
    op.drop_table("bq_evidence_candidates")
    op.drop_table("bq_document_sections")
    op.drop_table("bq_source_documents")
