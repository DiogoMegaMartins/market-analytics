"""Deterministic comparison of persisted valuation run snapshots."""
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

SCENARIOS = ("BEAR", "BASE", "BULL")
COMPARABLE_METRICS = (
    "enterprise_value",
    "equity_value",
    "value_per_share",
    "present_value_explicit_fcff",
    "present_value_terminal_value",
)


def _number(value: Any, field: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a valid decimal") from exc
    if not number.is_finite():
        raise ValueError(f"{field} must be finite")
    return number


def _delta(before: Decimal, after: Decimal) -> dict[str, str | None]:
    absolute = after - before
    percentage = absolute / before * Decimal(100) if before != 0 else None
    return {
        "absolute": str(absolute),
        "percentage": str(percentage) if percentage is not None else None,
    }


def _flatten_assumptions(value: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten nested JSON objects and arrays into stable dotted paths."""
    flattened: dict[str, Any] = {}
    if isinstance(value, Mapping) and value:
        for key in sorted(value, key=str):
            path = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(_flatten_assumptions(value[key], path))
    elif isinstance(value, list) and value:
        for index, item in enumerate(value):
            path = f"{prefix}.{index}" if prefix else str(index)
            flattened.update(_flatten_assumptions(item, path))
    else:
        flattened[prefix or "$"] = value
    return flattened


def compare_valuation_run_snapshots(
    baseline: Mapping[str, Any],
    comparison: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare two compatible persisted runs without recalculating either run."""
    for field in ("valuation_version", "method", "currency", "base_year"):
        if baseline.get(field) != comparison.get(field):
            raise ValueError(f"valuation runs have incompatible {field}")
    baseline_result = baseline.get("result")
    comparison_result = comparison.get("result")
    if not isinstance(baseline_result, Mapping) or not isinstance(comparison_result, Mapping):
        raise TypeError("valuation run results must be objects")
    old_scenarios = baseline_result.get("scenarios")
    new_scenarios = comparison_result.get("scenarios")
    if not isinstance(old_scenarios, Mapping) or not isinstance(new_scenarios, Mapping):
        raise TypeError("valuation run results must contain scenario objects")
    if set(old_scenarios) != set(SCENARIOS) or set(new_scenarios) != set(SCENARIOS):
        raise ValueError("valuation runs must contain BEAR, BASE, and BULL scenarios")

    scenario_deltas = {}
    for scenario in SCENARIOS:
        old_case = old_scenarios[scenario]
        new_case = new_scenarios[scenario]
        if not isinstance(old_case, Mapping) or not isinstance(new_case, Mapping):
            raise TypeError(f"{scenario} scenario results must be objects")
        scenario_deltas[scenario] = {}
        for metric in COMPARABLE_METRICS:
            if metric not in old_case or metric not in new_case:
                raise ValueError(f"{scenario} scenario is missing {metric}")
            old_value = _number(old_case[metric], f"baseline.{scenario}.{metric}")
            new_value = _number(new_case[metric], f"comparison.{scenario}.{metric}")
            scenario_deltas[scenario][metric] = {
                "baseline": str(old_value),
                "comparison": str(new_value),
                **_delta(old_value, new_value),
            }

    old_assumptions = baseline.get("assumptions")
    new_assumptions = comparison.get("assumptions")
    if not isinstance(old_assumptions, Mapping) or not isinstance(new_assumptions, Mapping):
        raise TypeError("valuation run assumptions must be objects")
    keys = sorted(set(old_assumptions) | set(new_assumptions))
    changed = [key for key in keys if old_assumptions.get(key) != new_assumptions.get(key)]

    old_flat = _flatten_assumptions(old_assumptions)
    new_flat = _flatten_assumptions(new_assumptions)
    missing = object()
    assumption_differences = []
    for path in sorted(set(old_flat) | set(new_flat)):
        old_value = old_flat.get(path, missing)
        new_value = new_flat.get(path, missing)
        if old_value != new_value:
            assumption_differences.append({
                "path": path,
                "baseline": None if old_value is missing else old_value,
                "comparison": None if new_value is missing else new_value,
                "baseline_present": old_value is not missing,
                "comparison_present": new_value is not missing,
            })
    return {
        "comparison_version": "valuation-run-comparison-v1",
        "method": baseline["method"],
        "valuation_version": baseline["valuation_version"],
        "base_year": baseline["base_year"],
        "currency": baseline["currency"],
        "baseline_run_id": str(baseline["id"]),
        "comparison_run_id": str(comparison["id"]),
        "changed_assumption_fields": changed,
        "changed_assumption_paths": [item["path"] for item in assumption_differences],
        "assumption_differences": assumption_differences,
        "scenarios": scenario_deltas,
        "analyst_review_required": True,
        "investment_recommendation": None,
        "limitations": [
            "Compares persisted outputs and assumptions; neither valuation is recalculated.",
            "Percentage changes are null when the baseline metric is zero.",
            "A numerical difference does not establish that an assumption is more accurate.",
            "Both runs must use the same method, engine version, base year, and currency.",
        ],
    }
