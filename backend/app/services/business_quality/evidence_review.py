"""Deterministic evidence review state and event hash helpers."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime

ALLOWED_TRANSITIONS = {"CANDIDATE": {"VERIFIED", "REJECTED", "SUPERSEDED"}}


def validate_evidence_transition(current: str, target: str, *, creator_id: str, actor_id: str, comment: str) -> None:
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise ValueError(f"Evidence transition {current} -> {target} is not allowed")
    if creator_id == actor_id:
        raise ValueError("Evidence creator cannot review their own candidate")
    if not comment.strip():
        raise ValueError("Review comment is required")


def build_review_event_hash(*, candidate_id: str, from_status: str | None, to_status: str,
                            actor_id: str, comment: str | None, previous_event_hash: str | None,
                            created_at: datetime) -> str:
    payload = {"candidate_id": candidate_id, "from_status": from_status, "to_status": to_status,
               "actor_id": actor_id, "comment": comment, "previous_event_hash": previous_event_hash,
               "created_at": created_at.isoformat()}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
