"""Deterministic Business Quality review state machine."""

TRANSITIONS = {
    ("DRAFT", "SUBMIT"): "SUBMITTED",
    ("REJECTED", "SUBMIT"): "SUBMITTED",
    ("SUBMITTED", "REVIEW"): "REVIEWED",
    ("REVIEWED", "APPROVE"): "APPROVED",
    ("REVIEWED", "REJECT"): "REJECTED",
}


def next_review_status(current: str, action: str, *, analyst_id: str | None, actor_id: str, comment: str | None) -> str:
    target = TRANSITIONS.get((current, action))
    if target is None:
        raise ValueError(f"Action {action} is not allowed from {current}")
    if action in {"REVIEW", "APPROVE", "REJECT"} and analyst_id and actor_id == analyst_id:
        raise ValueError("Reviewer/approver must be different from the submitting analyst")
    if action in {"APPROVE", "REJECT"} and not comment:
        raise ValueError("A review comment is required for approval or rejection")
    return target
