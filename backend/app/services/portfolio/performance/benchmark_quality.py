"""Read-only quality checks for manually supplied benchmark observations."""
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any


def build_benchmark_quality_report(
    observations: list[Any],
    *,
    max_gap_days: int = 7,
    anomaly_threshold_percent: Decimal = Decimal("20"),
) -> dict[str, Any]:
    """Report calendar gaps, unusually large moves, and missing provenance.

    Gaps use calendar days, not an exchange trading calendar. Large moves are
    review flags only and never invalidate or modify historical observations.
    """
    if not 1 <= max_gap_days <= 366:
        raise ValueError("max_gap_days must be between 1 and 366")
    try:
        threshold = Decimal(str(anomaly_threshold_percent))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("anomaly_threshold_percent must be a valid decimal") from exc
    if not threshold.is_finite() or threshold <= 0:
        raise ValueError("anomaly_threshold_percent must be finite and positive")

    ordered = sorted(observations, key=lambda item: item.observation_date)
    gaps: list[dict[str, Any]] = []
    anomalies: list[dict[str, str]] = []
    provenance_issues: list[dict[str, str]] = []

    for previous, current in zip(ordered, ordered[1:]):
        elapsed = (current.observation_date - previous.observation_date).days
        if elapsed > max_gap_days:
            gaps.append({
                "from_date": previous.observation_date.isoformat(),
                "to_date": current.observation_date.isoformat(),
                "elapsed_calendar_days": elapsed,
                "missing_calendar_days": elapsed - 1,
            })
        try:
            previous_level = Decimal(str(previous.index_level))
            current_level = Decimal(str(current.index_level))
            if (
                previous_level.is_finite() and current_level.is_finite()
                and previous_level > 0 and current_level > 0
            ):
                change_percent = (current_level / previous_level - Decimal(1)) * Decimal(100)
                if abs(change_percent) >= threshold:
                    anomalies.append({
                        "from_date": previous.observation_date.isoformat(),
                        "to_date": current.observation_date.isoformat(),
                        "change_percent": str(change_percent),
                        "reason": "absolute_change_meets_or_exceeds_review_threshold",
                    })
        except (InvalidOperation, TypeError, ValueError, ZeroDivisionError):
            # Persisted constraints normally prevent this; report generation stays resilient.
            continue

    for item in ordered:
        missing = [
            field for field in ("source", "methodology")
            if not str(getattr(item, field, "") or "").strip()
        ]
        if missing:
            provenance_issues.append({
                "observation_date": item.observation_date.isoformat(),
                "missing_fields": missing,
            })

    return {
        "observation_count": len(ordered),
        "first_observation_date": ordered[0].observation_date.isoformat() if ordered else None,
        "last_observation_date": ordered[-1].observation_date.isoformat() if ordered else None,
        "rules": {
            "gap_basis": "calendar_days",
            "max_gap_days": max_gap_days,
            "anomaly_threshold_percent": str(threshold),
            "anomalies_are_review_only": True,
            "source_reference_is_optional": True,
        },
        "summary": {
            "gap_count": len(gaps),
            "anomaly_count": len(anomalies),
            "provenance_issue_count": len(provenance_issues),
        },
        "gaps": gaps,
        "anomalies": anomalies,
        "provenance_issues": provenance_issues,
    }
