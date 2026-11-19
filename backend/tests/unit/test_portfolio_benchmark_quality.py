from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.portfolio.performance.benchmark_quality import build_benchmark_quality_report


def observation(day: int, level: str, *, source: str = "Official data", methodology: str = "Total return"):
    return SimpleNamespace(
        observation_date=date(2026, 1, day),
        index_level=Decimal(level),
        source=source,
        methodology=methodology,
    )


def test_quality_report_detects_calendar_gap_and_large_move_as_review_only():
    report = build_benchmark_quality_report(
        [observation(1, "100"), observation(12, "130")],
        max_gap_days=7,
        anomaly_threshold_percent=Decimal(20),
    )

    assert report["summary"] == {"gap_count": 1, "anomaly_count": 1, "provenance_issue_count": 0}
    assert report["gaps"][0]["missing_calendar_days"] == 10
    assert report["anomalies"][0]["change_percent"] == "30.0"
    assert report["rules"]["anomalies_are_review_only"] is True


def test_quality_report_flags_missing_source_and_methodology_but_not_optional_reference():
    item = observation(1, "100", source=" ", methodology="")
    report = build_benchmark_quality_report([item])

    assert report["provenance_issues"] == [{
        "observation_date": "2026-01-01",
        "missing_fields": ["source", "methodology"],
    }]
    assert report["rules"]["source_reference_is_optional"] is True


def test_quality_report_sorts_observations_and_handles_empty_series():
    report = build_benchmark_quality_report([observation(12, "100"), observation(1, "100")])
    assert report["first_observation_date"] == "2026-01-01"
    assert report["last_observation_date"] == "2026-01-12"
    assert build_benchmark_quality_report([])["observation_count"] == 0


@pytest.mark.parametrize("days", [0, 367])
def test_quality_report_rejects_invalid_gap_threshold(days):
    with pytest.raises(ValueError, match="max_gap_days"):
        build_benchmark_quality_report([], max_gap_days=days)


def test_quality_report_rejects_invalid_anomaly_threshold():
    with pytest.raises(ValueError, match="finite and positive"):
        build_benchmark_quality_report([], anomaly_threshold_percent=Decimal("NaN"))
