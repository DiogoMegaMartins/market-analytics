from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.metrics.calculator import MetricStatus, calculate_annual_metrics
from app.services.metrics.historical import QuarterlyObservation, calculate_ttm, detect_restatements


def _fact(value: str, filed: date, *, metric="FIN.REVENUE", year=2023):
    return SimpleNamespace(
        metric_id=metric, value=Decimal(value), unit="USD", currency="USD",
        period_kind="ANNUAL", fiscal_year=year, fiscal_period="FY",
        start_date=date(year, 1, 1), end_date=date(year, 12, 31), filed_at=filed,
    )


def test_detect_restatement_and_materiality():
    changes = detect_restatements([
        _fact("100", date(2024, 2, 1)), _fact("108", date(2024, 4, 1)),
        _fact("108", date(2024, 5, 1)),
    ])
    assert len(changes) == 1
    assert changes[0].absolute_change == Decimal(8)
    assert changes[0].material is True


def test_restatement_zero_base_is_material_but_relative_change_unknown():
    changes = detect_restatements([_fact("0", date(2024, 2, 1)), _fact("1", date(2024, 4, 1))])
    assert changes[0].relative_change is None
    assert changes[0].material is True


def test_restatement_threshold_is_configurable():
    changes = detect_restatements(
        [_fact("100", date(2024, 2, 1)), _fact("102", date(2024, 4, 1))],
        materiality_threshold=Decimal("0.05"),
    )
    assert changes[0].material is False


def _quarter(start, end, value):
    return QuarterlyObservation(
        metric_id="FIN.REVENUE", value=Decimal(value), unit="USD", currency="USD",
        start_date=date.fromisoformat(start), end_date=date.fromisoformat(end),
    )


def test_ttm_sums_four_consecutive_standalone_quarters():
    rows = [
        _quarter("2023-07-01", "2023-09-30", "20"),
        _quarter("2023-10-01", "2023-12-31", "25"),
        _quarter("2024-01-01", "2024-03-31", "30"),
        _quarter("2024-04-01", "2024-06-30", "35"),
    ]
    result = calculate_ttm(rows)
    assert result.value == Decimal(110)
    assert result.period_start == date(2023, 7, 1)
    assert result.period_end == date(2024, 6, 30)


def test_ttm_rejects_ytd_periods():
    rows = [
        _quarter("2023-01-01", "2023-03-31", "10"),
        _quarter("2023-01-01", "2023-06-30", "20"),
        _quarter("2023-01-01", "2023-09-30", "30"),
        _quarter("2023-01-01", "2023-12-31", "40"),
    ]
    with pytest.raises(ValueError, match="standalone quarterly"):
        calculate_ttm(rows)


def test_ttm_rejects_currency_mismatch():
    rows = [
        _quarter("2023-07-01", "2023-09-30", "20"),
        _quarter("2023-10-01", "2023-12-31", "25"),
        _quarter("2024-01-01", "2024-03-31", "30"),
        _quarter("2024-04-01", "2024-06-30", "35"),
    ]
    rows[-1] = QuarterlyObservation(**{**rows[-1].__dict__, "currency": "EUR"})
    with pytest.raises(ValueError, match="metric, unit and currency"):
        calculate_ttm(rows)


def test_gross_margin_requires_gross_profit_and_revenue():
    results = {item.metric_id: item for item in calculate_annual_metrics({
        "FIN.REVENUE": Decimal(200), "FIN.GROSS_PROFIT": Decimal(80),
    })}
    assert results["FIN.GROSS_MARGIN"].value == Decimal("0.4")
    missing = {item.metric_id: item for item in calculate_annual_metrics({"FIN.REVENUE": Decimal(200)})}
    assert missing["FIN.GROSS_MARGIN"].status == MetricStatus.UNAVAILABLE
