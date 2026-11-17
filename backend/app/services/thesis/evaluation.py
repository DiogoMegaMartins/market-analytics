"""Deterministic evaluation of explicit investment-thesis invalidation conditions."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def material_change(previous: Any, current: Any, *, threshold_percent: Decimal = Decimal(20)) -> dict[str, str] | None:
    """Return a deterministic material-change record using the absolute prior value as denominator."""
    try:
        before, after = Decimal(str(previous)), Decimal(str(current))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not before.is_finite() or not after.is_finite() or not threshold_percent.is_finite():
        return None
    if before == 0:
        if after == 0:
            return None
        percent = "UNBOUNDED_FROM_ZERO"
        material = True
    else:
        change = abs(after - before) / abs(before) * 100
        percent = format(change.normalize(), "f")
        material = change >= threshold_percent
    if not material:
        return None
    return {"previous_value": str(before), "current_value": str(after),
            "change_percent": percent, "threshold_percent": str(threshold_percent)}


def evaluate_thesis_assumptions(
    *, assumptions: list[dict[str, Any]], metrics: list[dict[str, Any]], fiscal_year: int
) -> dict[str, Any]:
    by_id = {str(item.get("metric_id")): item for item in metrics}
    evaluations = []
    for assumption in assumptions:
        metric_id = str(assumption["metric_id"])
        metric = by_id.get(metric_id)
        result = {
            "assumption_id": assumption["assumption_id"],
            "description": assumption["description"],
            "metric_id": metric_id,
            "condition": assumption["condition"],
            "threshold": str(assumption["threshold"]),
            "expected_unit": assumption["unit"],
            "observed_value": None,
            "observed_unit": None,
            "status": "UNKNOWN",
            "reason": None,
        }
        if metric is None:
            result["reason"] = "Metric is not available for the selected fiscal year."
        elif metric.get("status") != "CALCULATED" or metric.get("value") is None:
            result["reason"] = "Metric result is not CALCULATED."
        elif str(metric.get("unit")) != str(assumption["unit"]):
            result["status"] = "REVIEW_REQUIRED"
            result["observed_unit"] = metric.get("unit")
            result["reason"] = "Observed unit differs from the thesis assumption unit."
        else:
            try:
                value = Decimal(str(metric["value"]))
                threshold = Decimal(str(assumption["threshold"]))
            except (InvalidOperation, ValueError, TypeError):
                result["status"] = "REVIEW_REQUIRED"
                result["reason"] = "Metric or threshold is not a valid decimal."
            else:
                result["observed_value"] = str(value)
                result["observed_unit"] = metric.get("unit")
                if not value.is_finite() or not threshold.is_finite():
                    result["status"] = "REVIEW_REQUIRED"
                    result["reason"] = "Non-finite values cannot be evaluated."
                else:
                    breached = (
                        value > threshold if assumption["condition"] == "ABOVE"
                        else value < threshold
                    )
                    result["status"] = "BREACH_CANDIDATE" if breached else "NO_BREACH_DETECTED"
                    result["reason"] = "Deterministic threshold comparison; analyst review required."

        evaluations.append(result)

    statuses = {item["status"] for item in evaluations}
    if not evaluations:
        overall = "INSUFFICIENT_DATA"
    elif "BREACH_CANDIDATE" in statuses:
        overall = "BREACH_CANDIDATE"
    elif "REVIEW_REQUIRED" in statuses:
        overall = "REVIEW_REQUIRED"
    elif "UNKNOWN" in statuses:
        overall = "INSUFFICIENT_DATA"
    else:
        overall = "NO_BREACH_DETECTED"
    return {
        "fiscal_year": fiscal_year,
        "overall_status": overall,
        "assumption_evaluations": evaluations,
        "automatic_invalidation": False,
        "analyst_review_required": True,
        "limitations": [
            "Only the explicit conditions stored in this thesis version are evaluated.",
            "A threshold breach is a review trigger, not proof that the investment thesis is invalid.",
            "No missing metric is treated as a breach.",
            "No causal interpretation or investment recommendation is generated.",
        ],
    }
