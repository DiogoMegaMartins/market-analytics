from decimal import Decimal

import pytest

from app.services.valuation.dcf import calculate_fcff_dcf


def _period(year: int, revenue: str = "1000") -> dict:
    return {
        "year": year,
        "revenue": revenue,
        "ebit_margin": "0.20",
        "tax_rate": "0.25",
        "da": "40",
        "capex": "50",
        "change_nwc": "10",
    }


def _input() -> dict:
    periods = [_period(2025), _period(2026, "1100"), _period(2027, "1200")]
    return {
        "base_year": 2024,
        "currency": "USD",
        "scenarios": {
            "BEAR": [_period(2025, "900"), _period(2026, "950"), _period(2027, "1000")],
            "BASE": periods,
            "BULL": [_period(2025, "1100"), _period(2026, "1250"), _period(2027, "1400")],
        },
        "wacc": "0.09",
        "terminal_growth": "0.025",
        "net_debt": "100",
        "diluted_shares": "50",
    }


def test_fcff_dcf_returns_three_scenarios_and_sensitivity() -> None:
    result = calculate_fcff_dcf(**_input())

    assert result["method"] == "FCFF_DCF"
    assert result["valuation_version"] == "fcff-dcf-v1"
    assert set(result["scenarios"]) == {"BEAR", "BASE", "BULL"}
    assert Decimal(result["scenarios"]["BULL"]["value_per_share"]) > Decimal(
        result["scenarios"]["BASE"]["value_per_share"]
    )
    assert Decimal(result["scenarios"]["BASE"]["value_per_share"]) > Decimal(
        result["scenarios"]["BEAR"]["value_per_share"]
    )
    assert len(result["sensitivity"]) == 3
    assert all(len(row["values_per_share"]) == 3 for row in result["sensitivity"])
    assert result["analyst_review_required"] is True
    assert result["investment_recommendation"] is None


def test_fcff_formula_is_applied_to_each_forecast_period() -> None:
    result = calculate_fcff_dcf(**_input())

    # EBIT 200; NOPAT 150; FCFF = 150 + 40 - 50 - 10 = 130.
    assert Decimal(result["scenarios"]["BASE"]["fcff_by_year"][0]["fcff"]) == Decimal("130.00")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("wacc", "0", "wacc"),
        ("terminal_growth", "0.10", "terminal_growth"),
        ("diluted_shares", "0", "diluted_shares"),
        ("currency", "US", "currency"),
    ],
)
def test_rejects_invalid_global_assumptions(field: str, value: str, message: str) -> None:
    payload = _input()
    payload[field] = value

    with pytest.raises(ValueError, match=message):
        calculate_fcff_dcf(**payload)


def test_rejects_missing_scenario_or_inconsistent_years() -> None:
    payload = _input()
    payload["scenarios"].pop("BULL")
    with pytest.raises(ValueError, match="exactly BEAR"):
        calculate_fcff_dcf(**payload)

    payload = _input()
    payload["scenarios"]["BULL"][1]["year"] = 2028
    with pytest.raises(ValueError, match="consecutive"):
        calculate_fcff_dcf(**payload)


def test_rejects_non_finite_or_invalid_forecast_values() -> None:
    payload = _input()
    payload["scenarios"]["BASE"][0]["revenue"] = "NaN"
    with pytest.raises(ValueError, match="finite"):
        calculate_fcff_dcf(**payload)

    payload = _input()
    payload["scenarios"]["BASE"][0]["tax_rate"] = "1.1"
    with pytest.raises(ValueError, match="tax_rate"):
        calculate_fcff_dcf(**payload)


def test_terminal_value_concentration_is_a_warning_not_rejection() -> None:
    payload = _input()
    for scenario in payload["scenarios"].values():
        for period in scenario:
            period["revenue"] = "1000000"
    result = calculate_fcff_dcf(**payload)

    assert "PRESENT_VALUE_TERMINAL_VALUE_EXCEEDS_80_PERCENT_OF_EV" in result[
        "scenarios"
    ]["BASE"]["warnings"]


@pytest.mark.parametrize(
    ("scenarios", "message"),
    [
        (None, "scenarios must be an object"),
        ([], "scenarios must be an object"),
    ],
)
def test_rejects_non_object_scenarios(scenarios, message):
    payload = _input()
    payload["scenarios"] = scenarios
    with pytest.raises(ValueError, match=message):
        calculate_fcff_dcf(**payload)


@pytest.mark.parametrize(
    ("periods", "message"),
    [
        (None, "forecast periods must be a sequence"),
        ("not-a-period-list", "forecast periods must be a sequence"),
        ([None], "forecast periods must be objects"),
    ],
)
def test_rejects_malformed_forecast_period_collections(periods, message):
    payload = _input()
    payload["scenarios"]["BASE"] = periods
    with pytest.raises(ValueError, match=message):
        calculate_fcff_dcf(**payload)


def test_rejects_non_integer_forecast_year():
    payload = _input()
    payload["scenarios"]["BASE"][0]["year"] = 2025.5
    with pytest.raises(ValueError, match="forecast years must be consecutive"):
        calculate_fcff_dcf(**payload)
