from datetime import date
from decimal import Decimal

import pytest

from app.services.portfolio.performance.mwr import calculate_money_weighted_return


def _valuation(day, value, *, recorded="2026-02-01T00:00:00+00:00", identifier="a"):
    return {"valuation_date": day, "total_value": str(value), "recorded_at": recorded, "id": identifier}


def test_xirr_without_intermediate_flows_matches_annualized_period_return():
    result = calculate_money_weighted_return(
        [_valuation("2025-01-01", 100), _valuation("2026-01-01", 110)],
        [],
        start_date=date(2025, 1, 1),
        end_date=date(2026, 1, 1),
    )
    assert Decimal(result["money_weighted_return"]).quantize(Decimal("0.0001")) == Decimal("0.1000")
    assert result["method"] == "XIRR_ACTUAL_365"
    assert result["root_count"] == 1
    assert result["cash_flows"][0]["investor_cash_flow"] == "-100"
    assert result["cash_flows"][-1]["investor_cash_flow"] == "110"


def test_xirr_uses_deposits_as_negative_and_withdrawals_as_positive_flows():
    result = calculate_money_weighted_return(
        [_valuation("2025-01-01", 100), _valuation("2025-07-01", 160), _valuation("2026-01-01", 170)],
        [
            {"flow_date": "2025-04-01", "flow_type": "DEPOSIT", "amount": "50"},
            {"flow_date": "2025-07-01", "flow_type": "WITHDRAWAL", "amount": "10"},
        ],
        start_date=date(2025, 1, 1),
        end_date=date(2026, 1, 1),
    )
    flows = {item["date"]: Decimal(item["investor_cash_flow"]) for item in result["cash_flows"]}
    assert flows["2025-04-01"] == Decimal("-50")
    assert flows["2025-07-01"] == Decimal("10")
    assert flows["2025-01-01"] == Decimal("-100")
    assert flows["2026-01-01"] == Decimal("170")
    assert result["external_cash_flow_count"] == 2


def test_xirr_rejects_ambiguous_multiple_roots():
    with pytest.raises(ValueError, match="multiple roots"):
        calculate_money_weighted_return(
            [
                _valuation("2023-01-01", 100),
                _valuation("2024-01-01", 230),
                _valuation("2025-01-01", 132),
            ],
            [{"flow_date": "2024-01-01", "flow_type": "WITHDRAWAL", "amount": "230"}],
            start_date=date(2023, 1, 1),
            end_date=date(2025, 1, 1),
        )


def test_xirr_rejects_cash_flows_without_a_root():
    with pytest.raises(ValueError, match="no XIRR root"):
        calculate_money_weighted_return(
            [_valuation("2025-01-01", 100), _valuation("2026-01-01", 50)],
            [],
            start_date=date(2025, 1, 1),
            end_date=date(2026, 1, 1),
        )


@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-Infinity"])
def test_xirr_rejects_non_finite_valuations(bad):
    with pytest.raises(ValueError, match="finite"):
        calculate_money_weighted_return(
            [_valuation("2025-01-01", bad), _valuation("2026-01-01", 110)],
            [],
            start_date=date(2025, 1, 1),
            end_date=date(2026, 1, 1),
        )


def test_xirr_requires_positive_start_and_end_values():
    with pytest.raises(ValueError, match="starting portfolio value"):
        calculate_money_weighted_return(
            [_valuation("2025-01-01", 0), _valuation("2026-01-01", 110)],
            [],
            start_date=date(2025, 1, 1),
            end_date=date(2026, 1, 1),
        )


def test_latest_valuation_per_date_is_canonical():
    result = calculate_money_weighted_return(
        [
            _valuation("2025-01-01", 100),
            _valuation("2026-01-01", 105, recorded="2026-01-01T10:00:00+00:00", identifier="old"),
            _valuation("2026-01-01", 110, recorded="2026-01-01T11:00:00+00:00", identifier="new"),
        ],
        [],
        start_date=date(2025, 1, 1),
        end_date=date(2026, 1, 1),
    )
    assert Decimal(result["ending_value"]) == Decimal("110")
    assert Decimal(result["money_weighted_return"]).quantize(Decimal("0.0001")) == Decimal("0.1000")
