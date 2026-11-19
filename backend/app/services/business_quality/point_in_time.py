"""Point-in-time evidence eligibility for reproducible Business Quality datasets."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    criterion_key: str
    source_name: str
    source_url: str
    published_at: datetime | None
    available_at: datetime | None
    captured_at: datetime
    content_hash: str
    source_type: str = "PRIMARY"


@dataclass(frozen=True)
class EvidenceDecision:
    evidence_id: str
    eligible: bool
    reason: str


def evaluate_point_in_time_evidence(
    records: Sequence[EvidenceRecord], *, as_of: datetime
) -> tuple[EvidenceDecision, ...]:
    """Only admit evidence demonstrably public/available by the assessment cutoff.

    captured_at records when this system archived the item; it does not establish
    historical availability by itself. Missing publication/availability timestamps
    are marked unverifiable rather than assumed eligible.
    """
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    ids = [r.evidence_id for r in records]
    if any(not x.strip() for x in ids) or len(ids) != len(set(ids)):
        raise ValueError("Evidence IDs must be non-empty and unique")
    decisions: list[EvidenceDecision] = []
    for r in records:
        if not all(x.strip() for x in (r.criterion_key, r.source_name, r.source_url, r.content_hash)):
            raise ValueError(f"Evidence {r.evidence_id} is missing provenance metadata")
        if r.captured_at.tzinfo is None or r.captured_at.utcoffset() is None:
            raise ValueError(f"Evidence {r.evidence_id}: captured_at must be timezone-aware")
        if r.published_at is None or r.available_at is None:
            reason, eligible = "UNVERIFIABLE_AVAILABILITY_DATE", False
        elif r.published_at.tzinfo is None or r.available_at.tzinfo is None:
            raise ValueError(f"Evidence {r.evidence_id}: source timestamps must be timezone-aware")
        elif r.published_at > as_of or r.available_at > as_of:
            reason, eligible = "PUBLISHED_AFTER_CUTOFF", False
        else:
            reason, eligible = "AVAILABLE_AS_OF_CUTOFF", True
        decisions.append(EvidenceDecision(r.evidence_id, eligible, reason))
    return tuple(decisions)


def build_point_in_time_manifest(
    records: Sequence[EvidenceRecord], *, as_of: datetime
) -> dict:
    decisions = evaluate_point_in_time_evidence(records, as_of=as_of)
    return {
        "as_of": as_of.isoformat(),
        "policy_version": "PIT_EVIDENCE_1.0.0",
        "eligible_evidence_ids": [d.evidence_id for d in decisions if d.eligible],
        "excluded": [{"evidence_id": d.evidence_id, "reason": d.reason} for d in decisions if not d.eligible],
        "evidence": [
            {"evidence_id": r.evidence_id, "criterion_key": r.criterion_key,
             "source_name": r.source_name, "source_url": r.source_url,
             "published_at": r.published_at.isoformat() if r.published_at else None,
             "available_at": r.available_at.isoformat() if r.available_at else None,
             "captured_at": r.captured_at.isoformat(), "content_hash": r.content_hash,
             "source_type": r.source_type}
            for r in records
        ],
    }
