from datetime import date
from decimal import Decimal

import pytest

from app.services.portfolio.performance.twr import calculate_time_weighted_return


def _valuation(day, value, *, recorded="2026-02-01T00:00:00+00:00", identifier="a"):
    return {"valuation_date": day, "total_value": str(value), "recorded_at": recorded, "id": identifier}


def test_twr_without_external_flows_is_simple_period_return():
    result = calculate_time_weighted_return(
        [_valuation("2026-01-01", 100), _valuation("2026-01-31", 120)],
        [], start_date=date(2026, 1, 1), end_date=date(2026, 1, 31),
    )
    assert Decimal(result["time_weighted_return"]) == Decimal("0.2")
    assert result["subperiod_count"] == 1


def test_twr_removes_deposit_from_investment_performance():
    result = calculate_time_weighted_return(
        [_valuation("2026-01-01", 100), _valuation("2026-01-15", 150), _valuation("2026-01-31", 165)],
        [{"flow_date": "2026-01-15", "flow_type": "DEPOSIT", "amount": "50"}],
        start_date=date(2026, 1, 1), end_date=date(2026, 1, 31),
    )
    assert Decimal(result["time_weighted_return"]).quantize(Decimal("0.0001")) == Decimal("0.1000")
    assert result["subperiod_count"] == 2


def test_twr_handles_withdrawal_as_negative_external_flow():
    result = calculate_time_weighted_return(
        [_valuation("2026-01-01", 100), _valuation("2026-01-15", 50), _valuation("2026-01-31", 55)],
        [{"flow_date": "2026-01-15", "flow_type": "WITHDRAWAL", "amount": "50"}],
        start_date=date(2026, 1, 1), end_date=date(2026, 1, 31),
    )
    assert Decimal(result["time_weighted_return"]).quantize(Decimal("0.0001")) == Decimal("0.1000")


def test_twr_requires_valuation_on_flow_date_and_start_end_dates():
    flows = [{"flow_date": "2026-01-15", "flow_type": "DEPOSIT", "amount": "10"}]
    with pytest.raises(ValueError, match="external cash-flow date"):
        calculate_time_weighted_return(
            [_valuation("2026-01-01", 100), _valuation("2026-01-31", 120)],
            flows, start_date=date(2026, 1, 1), end_date=date(2026, 1, 31),
        )
    with pytest.raises(ValueError, match="starting valuation"):
        calculate_time_weighted_return(
            [_valuation("2026-01-31", 120)], [],
            start_date=date(2026, 1, 1), end_date=date(2026, 1, 31),
        )


def test_latest_recorded_valuation_is_canonical_for_same_date():
    result = calculate_time_weighted_return(
        [
            _valuation("2026-01-01", 100),
            _valuation("2026-01-31", 110, recorded="2026-01-31T10:00:00+00:00", identifier="old"),
            _valuation("2026-01-31", 120, recorded="2026-01-31T11:00:00+00:00", identifier="new"),
        ], [], start_date=date(2026, 1, 1), end_date=date(2026, 1, 31),
    )
    assert Decimal(result["ending_value"]) == 120
    assert Decimal(result["time_weighted_return"]) == Decimal("0.2")


@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-Infinity"])
def test_twr_rejects_non_finite_valuation_values(bad):
    with pytest.raises(ValueError, match="finite"):
        calculate_time_weighted_return(
            [_valuation("2026-01-01", bad), _valuation("2026-01-31", 120)],
            [], start_date=date(2026, 1, 1), end_date=date(2026, 1, 31),
        )


def test_twr_rejects_non_positive_capital_after_withdrawal():
    with pytest.raises(ValueError, match="non-positive invested capital"):
        calculate_time_weighted_return(
            [_valuation("2026-01-01", 100), _valuation("2026-01-15", 0)],
            [{"flow_date": "2026-01-15", "flow_type": "WITHDRAWAL", "amount": "100"}],
            start_date=date(2026, 1, 1), end_date=date(2026, 1, 15),
        )
