import pytest

from app.services.valuation.comparison import compare_valuation_run_snapshots


def _run(run_id: str, revenue: str = "1000") -> dict:
    scenarios = {}
    for scenario, multiplier in (("BEAR", "0.8"), ("BASE", "1"), ("BULL", "1.2")):
        value = str(float(revenue) * float(multiplier))
        scenarios[scenario] = {
            "enterprise_value": value,
            "equity_value": str(float(value) - 100),
            "value_per_share": str((float(value) - 100) / 50),
            "present_value_explicit_fcff": "200",
            "present_value_terminal_value": str(float(value) - 200),
        }
    return {
        "id": run_id,
        "valuation_version": "fcff-dcf-v1",
        "method": "FCFF_DCF",
        "base_year": 2024,
        "currency": "USD",
        "assumptions": {"wacc": "0.09", "terminal_growth": "0.025", "revenue": revenue},
        "result": {"scenarios": scenarios},
    }


def test_comparison_reports_scenario_deltas_and_changed_assumptions():
    result = compare_valuation_run_snapshots(_run("baseline"), _run("new", "1200"))
    assert result["baseline_run_id"] == "baseline"
    assert result["comparison_run_id"] == "new"
    assert result["changed_assumption_fields"] == ["revenue"]
    delta = result["scenarios"]["BASE"]["enterprise_value"]
    assert delta["baseline"] == "1000.0" and delta["comparison"] == "1200.0"
    assert delta["absolute"] == "200.0" and delta["percentage"] == "20.0"
    assert result["analyst_review_required"] is True
    assert result["investment_recommendation"] is None


def test_zero_baseline_has_null_percentage_delta():
    before, after = _run("baseline"), _run("after")
    before["result"]["scenarios"]["BASE"]["value_per_share"] = "0"
    after["result"]["scenarios"]["BASE"]["value_per_share"] = "10"
    result = compare_valuation_run_snapshots(before, after)
    delta = result["scenarios"]["BASE"]["value_per_share"]
    assert delta["absolute"] == "10"
    assert delta["percentage"] is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("valuation_version", "fcff-dcf-v2"),
        ("method", "DDM"),
        ("currency", "EUR"),
        ("base_year", 2025),
    ],
)
def test_rejects_incompatible_runs(field, value):
    baseline, comparison = _run("baseline"), _run("comparison")
    comparison[field] = value
    with pytest.raises(ValueError, match=f"incompatible {field}"):
        compare_valuation_run_snapshots(baseline, comparison)


def test_rejects_missing_or_non_finite_metrics():
    baseline, comparison = _run("baseline"), _run("comparison")
    del comparison["result"]["scenarios"]["BASE"]["enterprise_value"]
    with pytest.raises(ValueError, match="missing enterprise_value"):
        compare_valuation_run_snapshots(baseline, comparison)
    comparison = _run("comparison")
    comparison["result"]["scenarios"]["BASE"]["enterprise_value"] = "NaN"
    with pytest.raises(ValueError, match="finite"):
        compare_valuation_run_snapshots(baseline, comparison)
