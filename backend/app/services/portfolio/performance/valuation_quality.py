"""Read-only quality diagnostics for immutable portfolio valuation snapshots."""
from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from itertools import pairwise
from typing import Any


def build_portfolio_valuation_quality_report(snapshots: Sequence[Any], *, max_gap_days: int = 7) -> dict[str, Any]:
    """Report date coverage, duplicate dates, canonical selection and provenance.

    Canonical policy matches TWR/MWR: greatest (recorded_at, id).
    Gaps use calendar days; source_reference is intentionally optional.
    """
    if not 1 <= max_gap_days <= 366:
        raise ValueError("max_gap_days must be between 1 and 366")
    by_date: dict[date, list[Any]] = defaultdict(list)
    for item in snapshots:
        by_date[item.valuation_date].append(item)
    dates = sorted(by_date)
    gaps, duplicates, provenance, canonical = [], [], [], []
    for previous, current in pairwise(dates):
        elapsed = (current - previous).days
        if elapsed > max_gap_days:
            gaps.append({"from_date": previous.isoformat(), "to_date": current.isoformat(),
                         "elapsed_calendar_days": elapsed, "missing_calendar_days": elapsed - 1})
    for observed in dates:
        items = by_date[observed]
        selected = max(items, key=lambda item: (item.recorded_at, str(item.id)))
        canonical.append({"valuation_date": observed.isoformat(), "snapshot_id": str(selected.id),
                          "recorded_at": selected.recorded_at.isoformat(),
                          "total_value": str(selected.market_value + selected.cash_value)})
        if len(items) > 1:
            duplicates.append({"valuation_date": observed.isoformat(), "snapshot_count": len(items),
                               "canonical_snapshot_id": str(selected.id),
                               "canonical_recorded_at": selected.recorded_at.isoformat(),
                               "superseded_snapshot_ids": sorted(str(x.id) for x in items if x.id != selected.id)})
        for item in items:
            missing = [field for field in ("valuation_source", "methodology")
                       if not str(getattr(item, field, "") or "").strip()]
            if missing:
                provenance.append({"valuation_date": observed.isoformat(), "snapshot_id": str(item.id),
                                    "missing_fields": missing})
    return {
        "snapshot_count": len(snapshots), "valuation_date_count": len(dates),
        "first_valuation_date": dates[0].isoformat() if dates else None,
        "last_valuation_date": dates[-1].isoformat() if dates else None,
        "rules": {"canonical_selection": "greatest_recorded_at_then_greatest_id",
                  "gap_basis": "calendar_days", "max_gap_days": max_gap_days,
                  "source_reference_is_optional": True, "findings_are_review_only": True},
        "summary": {"gap_count": len(gaps), "duplicate_date_count": len(duplicates),
                    "extra_snapshot_count": sum(x["snapshot_count"] - 1 for x in duplicates),
                    "provenance_issue_count": len(provenance)},
        "gaps": gaps, "duplicate_dates": duplicates, "provenance_issues": provenance,
        "canonical_observations": canonical,
    }
