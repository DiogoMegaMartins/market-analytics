from datetime import UTC, datetime

import pytest

from app.services.business_quality.evidence_review import (
    build_review_event_hash,
    validate_evidence_transition,
)


def test_review_requires_independent_reviewer_and_comment():
    with pytest.raises(ValueError, match="cannot review"):
        validate_evidence_transition("CANDIDATE", "VERIFIED", creator_id="a", actor_id="a", comment="ok")
    with pytest.raises(ValueError, match="comment"):
        validate_evidence_transition("CANDIDATE", "VERIFIED", creator_id="a", actor_id="b", comment=" ")


def test_only_candidate_can_transition_once():
    validate_evidence_transition("CANDIDATE", "VERIFIED", creator_id="a", actor_id="b", comment="Checked against filing")
    with pytest.raises(ValueError, match="not allowed"):
        validate_evidence_transition("VERIFIED", "REJECTED", creator_id="a", actor_id="c", comment="Changed")


def test_event_hash_is_deterministic_and_chained():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    kwargs = {
        "candidate_id": "c1",
        "from_status": "CANDIDATE",
        "to_status": "VERIFIED",
        "actor_id": "reviewer",
        "comment": "Verified",
        "previous_event_hash": "a" * 64,
        "created_at": now,
    }
    first = build_review_event_hash(**kwargs)
    assert first == build_review_event_hash(**kwargs)
    assert first != build_review_event_hash(**{**kwargs, "previous_event_hash": "b" * 64})
