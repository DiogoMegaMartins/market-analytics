"""Deterministic comparison of company research snapshots.

This reports observable changes only. It does not infer causality or investment
conclusions, and it never modifies Business Quality or valuation outputs.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

WHAT_CHANGED_VERSION = "what-changed-v1.0.0"


def _passage_key(item: dict[str, Any]) -> tuple[str, str, str, str]:
    source = item.get("source") or {}
    return (
        str(item.get("criterion_key") or ""),
        str(item.get("passage_type") or ""),
        str(source.get("document_id") or ""),
        str(source.get("section_id") or ""),
    )


def _dimension_scores(assessment: dict[str, Any] | None) -> dict[str, Decimal]:
    if not assessment:
        return {}
    dimensions = (assessment.get("results") or {}).get("dimensions") or []
    output: dict[str, Decimal] = {}
    for dimension in dimensions:
        name, score = str(dimension.get("dimension") or ""), dimension.get("score")
        if name and score is not None:
            try:
                parsed = Decimal(str(score))
            except (InvalidOperation, ValueError):
                continue
            if parsed.is_finite():
                output[name] = parsed
    return output


def _assessment_summary(assessment: dict[str, Any] | None) -> dict[str, Any] | None:
    if assessment is None:
        return None
    return {
        "id": str(assessment.get("id")),
        "created_at": assessment.get("created_at"),
        "engine_version": assessment.get("engine_version"),
        "rubric_version": assessment.get("rubric_version"),
        "status": assessment.get("status"),
        "score": str(assessment.get("overall_score")) if assessment.get("overall_score") is not None else None,
        "classification": assessment.get("classification"),
        "dimensions": {k: str(v) for k, v in _dimension_scores(assessment).items()},
    }


def build_what_changed(
    *, company_id: str, company_name: str, from_date: date, to_date: date,
    before_brief: dict[str, Any], after_brief: dict[str, Any],
    before_assessment: dict[str, Any] | None = None,
    after_assessment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if from_date >= to_date:
        raise ValueError("from_date must be earlier than to_date")

    before_docs = {str(d["document_id"]): d for d in before_brief.get("source_documents", [])}
    after_docs = {str(d["document_id"]): d for d in after_brief.get("source_documents", [])}
    added_docs = [after_docs[k] for k in sorted(after_docs.keys() - before_docs.keys())]
    removed_docs = [before_docs[k] for k in sorted(before_docs.keys() - after_docs.keys())]

    before_passages = {_passage_key(p): p for p in before_brief.get("evidence_candidates", [])}
    after_passages = {_passage_key(p): p for p in after_brief.get("evidence_candidates", [])}
    new_passages = [after_passages[k] for k in sorted(after_passages.keys() - before_passages.keys())]
    no_longer_retrieved = [before_passages[k] for k in sorted(before_passages.keys() - after_passages.keys())]

    old_scores, new_scores = _dimension_scores(before_assessment), _dimension_scores(after_assessment)
    score_changes = []
    for dimension in sorted(old_scores.keys() | new_scores.keys()):
        old, new = old_scores.get(dimension), new_scores.get(dimension)
        if old != new:
            score_changes.append({
                "dimension": dimension,
                "previous_score": str(old) if old is not None else None,
                "current_score": str(new) if new is not None else None,
                "delta": str(new - old) if old is not None and new is not None else None,
                "status": "CHANGED" if old is not None and new is not None else "NEW_OR_MISSING",
            })

    before_summary = before_brief.get("summary") or {}
    after_summary = after_brief.get("summary") or {}
    count_changes = {}
    for key in ("candidate_passage_count", "risk_disclosure_count",
                "management_assertion_count", "quantitative_claim_count",
                "potential_conflict_count"):
        previous, current = int(before_summary.get(key, 0)), int(after_summary.get(key, 0))
        count_changes[key] = {"previous": previous, "current": current, "delta": current - previous}

    changes = []
    if added_docs:
        changes.append({"type": "NEW_FILINGS", "count": len(added_docs), "severity": "INFO"})
    if new_passages:
        changes.append({"type": "NEW_EVIDENCE_CANDIDATES", "count": len(new_passages), "severity": "REVIEW"})
    if score_changes:
        changes.append({"type": "BUSINESS_QUALITY_ASSESSMENT_CHANGED", "count": len(score_changes), "severity": "REVIEW"})
    if not changes:
        changes.append({"type": "NO_DETECTED_CHANGE", "count": 0, "severity": "INFO"})

    return {
        "version": WHAT_CHANGED_VERSION,
        "company_id": company_id,
        "company_name": company_name,
        "comparison": {"from_date": from_date.isoformat(), "to_date": to_date.isoformat()},
        "changes": changes,
        "filings": {
            "previous_count": len(before_docs), "current_count": len(after_docs),
            "added": added_docs, "no_longer_in_snapshot": removed_docs,
        },
        "evidence": {
            "new_candidates": new_passages,
            "no_longer_retrieved": no_longer_retrieved,
            "counts": count_changes,
        },
        "business_quality": {
            "previous_assessment": _assessment_summary(before_assessment),
            "current_assessment": _assessment_summary(after_assessment),
            "dimension_changes": score_changes,
        },
        "interpretation": {
            "causality_established": False,
            "business_quality_score_modified": False,
            "fair_value_modified": False,
            "investment_recommendation_generated": False,
            "limitations": [
                "Only filings already ingested at query time are compared.",
                "A passage no longer retrieved is not proof that the underlying risk or claim disappeared.",
                "Assessment differences may reflect analyst inputs, methodology, or evidence changes.",
                "Filing date is used as the cutoff; exact public availability time is not established.",
                "No causal relationship or investment implication is inferred.",
            ],
        },
        "analyst_review_required": True,
    }
