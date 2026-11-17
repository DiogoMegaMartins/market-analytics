from app.models.business_quality_evidence import (
    BQDocumentSection,
    BQEvidenceCandidate,
    BQSourceDocument,
)


def test_evidence_persistence_tables_are_registered_with_provenance_fields():
    expected = {
        BQSourceDocument: {"company_id", "accession_number", "filed_at", "source_url", "document_hash", "original_content"},
        BQDocumentSection: {"document_id", "section_key", "sequence_number", "text_content", "content_hash"},
        BQEvidenceCandidate: {"company_id", "document_id", "section_id", "criterion_key", "passage", "status", "evidence_hash", "created_by"},
    }
    for model, columns in expected.items():
        assert columns.issubset(set(model.__table__.columns.keys()))


def test_evidence_status_is_explicit_and_not_auto_verified():
    assert BQEvidenceCandidate.__table__.c.status.nullable is False
    assert BQEvidenceCandidate.__table__.c.reviewed_by.nullable is True
    assert BQEvidenceCandidate.__table__.c.evidence_hash.nullable is False


def test_evidence_workspace_uses_existing_persisted_provenance_models():
    # The review workspace is a read/review surface over the existing immutable source
    # and audit records; it must not introduce a second evidence-of-record store.
    from app.models.business_quality_evidence_audit import BQEvidenceReviewEvent

    assert {"candidate_id", "from_status", "to_status", "actor_id", "event_hash"}.issubset(
        set(BQEvidenceReviewEvent.__table__.columns.keys())
    )
    assert BQSourceDocument.__table__.c.original_content.nullable is False
    assert BQDocumentSection.__table__.c.content_hash.nullable is False
