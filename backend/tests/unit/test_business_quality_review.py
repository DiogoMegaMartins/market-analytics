import pytest

from app.services.business_quality.review import next_review_status


def test_happy_path_and_rejection_resubmission():
    status = next_review_status("DRAFT", "SUBMIT", analyst_id="a1", actor_id="a1", comment=None)
    assert status == "SUBMITTED"
    status = next_review_status(status, "REVIEW", analyst_id="a1", actor_id="r1", comment="Checked")
    assert status == "REVIEWED"
    status = next_review_status(status, "REJECT", analyst_id="a1", actor_id="r1", comment="Need stronger evidence")
    assert status == "REJECTED"
    assert next_review_status(status, "SUBMIT", analyst_id="a1", actor_id="a1", comment=None) == "SUBMITTED"


def test_analyst_cannot_review_own_assessment():
    with pytest.raises(ValueError, match="different"):
        next_review_status("SUBMITTED", "REVIEW", analyst_id="same", actor_id="same", comment=None)


def test_terminal_transition_requires_reviewed_state_and_comment():
    with pytest.raises(ValueError, match="not allowed"):
        next_review_status("SUBMITTED", "APPROVE", analyst_id="a1", actor_id="r1", comment="OK")
    with pytest.raises(ValueError, match="comment"):
        next_review_status("REVIEWED", "APPROVE", analyst_id="a1", actor_id="r1", comment=None)


def test_invalid_action_rejected():
    with pytest.raises(ValueError):
        next_review_status("DRAFT", "APPROVE", analyst_id="a1", actor_id="r1", comment="OK")
