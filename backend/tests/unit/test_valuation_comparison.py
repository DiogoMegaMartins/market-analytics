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
    assert result["changed_assumption_paths"] == ["revenue"]
    assert result["assumption_differences"] == [{
        "path": "revenue", "json_pointer": "/revenue", "baseline": "1000", "comparison": "1200",
        "baseline_present": True, "comparison_present": True,
    }]
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



def test_reports_nested_scenario_assumption_paths_and_values():
    baseline, comparison = _run("baseline"), _run("comparison")
    baseline["assumptions"]["scenarios"] = {
        "BASE": [{"year": 2025, "revenue": "1000", "ebit_margin": "0.20"}]
    }
    comparison["assumptions"]["scenarios"] = {
        "BASE": [{"year": 2025, "revenue": "1250", "ebit_margin": "0.22"}]
    }
    result = compare_valuation_run_snapshots(baseline, comparison)
    assert result["changed_assumption_fields"] == ["scenarios"]
    assert result["changed_assumption_paths"] == [
        "scenarios.BASE.0.ebit_margin", "scenarios.BASE.0.revenue"
    ]
    assert result["assumption_differences"] == [
        {
            "path": "scenarios.BASE.0.ebit_margin",
            "json_pointer": "/scenarios/BASE/0/ebit_margin",
            "baseline": "0.20",
            "comparison": "0.22",
            "baseline_present": True,
            "comparison_present": True,
        },
        {
            "path": "scenarios.BASE.0.revenue",
            "json_pointer": "/scenarios/BASE/0/revenue",
            "baseline": "1000",
            "comparison": "1250",
            "baseline_present": True,
            "comparison_present": True,
        },
    ]


def test_reports_added_removed_and_null_assumption_values():
    baseline, comparison = _run("baseline"), _run("comparison")
    baseline["assumptions"]["optional"] = None
    comparison["assumptions"].pop("revenue")
    comparison["assumptions"]["scenarios"] = {"BASE": [{"year": 2025, "new_driver": "5"}]}
    result = compare_valuation_run_snapshots(baseline, comparison)
    by_path = {item["path"]: item for item in result["assumption_differences"]}
    assert by_path["optional"]["baseline_present"] is True
    assert by_path["optional"]["comparison_present"] is False
    assert by_path["revenue"]["baseline"] == "1000"
    assert by_path["revenue"]["comparison_present"] is False
    assert by_path["scenarios.BASE.0.new_driver"]["baseline_present"] is False
    assert by_path["scenarios.BASE.0.new_driver"]["comparison"] == "5"


def test_json_pointer_escapes_special_object_keys_without_collisions():
    baseline, comparison = _run("baseline"), _run("comparison")
    baseline["assumptions"] = {"a.b": {"c/d": "old"}, "a": {"b.c/d": "same"}, "tilde~key": "old"}
    comparison["assumptions"] = {"a.b": {"c/d": "new"}, "a": {"b.c/d": "changed"}, "tilde~key": "new"}
    result = compare_valuation_run_snapshots(baseline, comparison)
    by_pointer = {item["json_pointer"]: item for item in result["assumption_differences"]}
    assert set(by_pointer) == {"/a.b/c~1d", "/a/b.c~1d", "/tilde~0key"}
    assert by_pointer["/a.b/c~1d"]["path"] == "a.b.c/d"
    assert by_pointer["/a.b/c~1d"]["baseline"] == "old"
