"""Deterministic financial evolution and materiality classification."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

EVOLUTION_VERSION = "financial-evolution-v1.0.0"
VALID_STATUSES = {"CALCULATED"}
DEFAULT_MATERIALITY_THRESHOLD_PCT = Decimal(10)


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return parsed if parsed.is_finite() else None


def _classify_change(previous: Decimal, current: Decimal, threshold_pct: Decimal) -> tuple[str, Decimal | None]:
    # Relative changes are only meaningful when the prior value is positive.
    if previous <= 0:
        return "REVIEW_REQUIRED", None
    pct = (current - previous) / abs(previous) * Decimal(100)
    if abs(pct) >= threshold_pct:
        return "MATERIAL", pct
    return "NON_MATERIAL", pct


def build_financial_evolution(
    *, company_id: str, from_fiscal_year: int, to_fiscal_year: int,
    previous_metrics: list[dict[str, Any]], current_metrics: list[dict[str, Any]],
    threshold_pct: Decimal = DEFAULT_MATERIALITY_THRESHOLD_PCT,
) -> dict[str, Any]:
    if from_fiscal_year >= to_fiscal_year:
        raise ValueError("from_fiscal_year must be earlier than to_fiscal_year")
    if not threshold_pct.is_finite() or threshold_pct <= 0 or threshold_pct > 1000:
        raise ValueError("threshold_pct must be between 0 and 1000")

    old = {str(m["metric_id"]): m for m in previous_metrics}
    new = {str(m["metric_id"]): m for m in current_metrics}
    comparisons = []
    for metric_id in sorted(old.keys() | new.keys()):
        before, after = old.get(metric_id), new.get(metric_id)
        before_status = str(before.get("status", "UNKNOWN")) if before else "MISSING"
        after_status = str(after.get("status", "UNKNOWN")) if after else "MISSING"
        unit_before = str(before.get("unit", "")) if before else ""
        unit_after = str(after.get("unit", "")) if after else ""
        old_value = _decimal(before.get("value")) if before else None
        new_value = _decimal(after.get("value")) if after else None

        row = {
            "metric_id": metric_id,
            "previous": {"value": str(old_value) if old_value is not None else None,
                         "unit": unit_before, "status": before_status},
            "current": {"value": str(new_value) if new_value is not None else None,
                        "unit": unit_after, "status": after_status},
            "absolute_change": None, "percentage_change": None,
            "materiality": "NOT_ASSESSED", "reason": None,
        }
        if before is None or after is None:
            row["reason"] = "Metric is missing from one of the selected annual runs."
        elif before_status not in VALID_STATUSES or after_status not in VALID_STATUSES:
            row["reason"] = "Both periods must have CALCULATED status."
        elif unit_before != unit_after:
            row["materiality"] = "REVIEW_REQUIRED"
            row["reason"] = "Units differ; comparison is blocked."
        elif old_value is None or new_value is None:
            row["reason"] = "A finite numeric value is unavailable."
        else:
            delta = new_value - old_value
            materiality, pct = _classify_change(old_value, new_value, threshold_pct)
            row["absolute_change"] = str(delta)
            row["percentage_change"] = str(pct) if pct is not None else None
            row["materiality"] = materiality
            row["reason"] = (
                f"Absolute percentage change compared with the prior value; threshold {threshold_pct}%."
                if pct is not None else
                "Prior value is zero or negative; relative materiality is not reliable."
            )
        comparisons.append(row)

    material = [r for r in comparisons if r["materiality"] == "MATERIAL"]
    review = [r for r in comparisons if r["materiality"] == "REVIEW_REQUIRED"]
    return {
        "version": EVOLUTION_VERSION,
        "company_id": company_id,
        "comparison": {"from_fiscal_year": from_fiscal_year, "to_fiscal_year": to_fiscal_year},
        "materiality_policy": {
            "method": "absolute relative change",
            "threshold_pct": str(threshold_pct),
            "status": "HEURISTIC_REQUIRES_ANALYST_CALIBRATION",
            "sector_specific": False,
        },
        "summary": {
            "metrics_compared": len(comparisons),
            "material_changes": len(material),
            "review_required": len(review),
            "not_assessed": sum(r["materiality"] == "NOT_ASSESSED" for r in comparisons),
        },
        "metrics": comparisons,
        "interpretation": {
            "causality_established": False,
            "thesis_status_changed": False,
            "business_quality_modified": False,
            "fair_value_modified": False,
            "investment_recommendation_generated": False,
            "limitations": [
                "Only the latest persisted metric run for each selected fiscal year is compared.",
                "A 10% relative threshold is an initial heuristic, not a validated materiality standard.",
                "The threshold is not sector- or metric-specific and requires analyst calibration.",
                "Negative or zero prior values are flagged for review rather than assigned relative materiality.",
                "A material metric movement is not proof of a material change to the investment thesis.",
            ],
        },
        "analyst_review_required": True,
    }
