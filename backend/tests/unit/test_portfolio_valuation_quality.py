from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.services.portfolio.performance.valuation_quality import (
    build_portfolio_valuation_quality_report,
)
import pytest


def _snapshot(day, identifier, *, recorded="2026-01-01T10:00:00+00:00", source="MANUAL", methodology="Closing NAV"):
    return SimpleNamespace(valuation_date=date.fromisoformat(day), id=identifier,
        recorded_at=datetime.fromisoformat(recorded), market_value=Decimal(100),
        cash_value=Decimal(10), valuation_source=source, methodology=methodology)


def test_report_exposes_duplicate_date_and_canonical_policy():
    report = build_portfolio_valuation_quality_report([
        _snapshot("2026-01-01", "a"),
        _snapshot("2026-01-02", "old", recorded="2026-01-02T10:00:00+00:00"),
        _snapshot("2026-01-02", "new", recorded="2026-01-02T11:00:00+00:00"),
    ])
    assert report["summary"]["duplicate_date_count"] == 1
    assert report["summary"]["extra_snapshot_count"] == 1
    assert report["duplicate_dates"][0]["canonical_snapshot_id"] == "new"
    assert report["duplicate_dates"][0]["superseded_snapshot_ids"] == ["old"]
    assert report["canonical_observations"][1]["snapshot_id"] == "new"
    assert report["rules"]["canonical_selection"] == "greatest_recorded_at_then_greatest_id"


def test_report_uses_id_tiebreaker_and_flags_gaps_and_provenance():
    report = build_portfolio_valuation_quality_report([
        _snapshot("2026-01-01", "a"),
        _snapshot("2026-01-01", "z", source="", methodology=" "),
        _snapshot("2026-01-12", "b"),
    ], max_gap_days=7)
    assert report["duplicate_dates"][0]["canonical_snapshot_id"] == "z"
    assert report["summary"]["gap_count"] == 1
    assert report["gaps"][0]["missing_calendar_days"] == 10
    assert report["summary"]["provenance_issue_count"] == 1
    assert report["rules"]["source_reference_is_optional"] is True


def test_empty_report_is_well_formed():
    report = build_portfolio_valuation_quality_report([])
    assert report["snapshot_count"] == 0 and report["first_valuation_date"] is None
    assert report["canonical_observations"] == []


@pytest.mark.parametrize("days", [0, -1, 367])
def test_max_gap_days_must_be_bounded(days):
    with pytest.raises(ValueError, match="max_gap_days"):
        build_portfolio_valuation_quality_report([], max_gap_days=days)
