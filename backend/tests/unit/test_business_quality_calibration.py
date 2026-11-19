from decimal import Decimal

import pytest

from app.services.business_quality.calibration import CalibrationCompany, run_weight_sensitivity
from app.services.business_quality.engine import DIMENSIONS

KEYS = [d.key.value for d in DIMENSIONS]
EQUAL = {key: Decimal(20) for key in KEYS}


def test_weight_sensitivity_reports_score_and_rank_ranges():
    companies = [
        CalibrationCompany("A", {k: Decimal(90) if k == KEYS[0] else Decimal(50) for k in KEYS}),
        CalibrationCompany("B", {k: Decimal(50) if k == KEYS[0] else Decimal(90) for k in KEYS}),
    ]
    scenarios = {
        "equal": EQUAL,
        "business_model_heavy": {KEYS[0]: Decimal(60), **{k: Decimal(10) for k in KEYS[1:]}},
    }
    report = run_weight_sensitivity(companies, scenarios)
    assert len(report.scenarios) == 2
    assert report.scenarios[0].ranks == {"A": 2, "B": 1}
    assert report.scenarios[1].ranks == {"A": 1, "B": 2}
    assert {item.min_rank for item in report.sensitivity} == {1}
    assert {item.max_rank for item in report.sensitivity} == {2}
    assert all(item.min_score <= item.max_score for item in report.sensitivity)


def test_scenario_weights_must_sum_to_100():
    company = CalibrationCompany("A", {k: Decimal(70) for k in KEYS})
    with pytest.raises(ValueError, match="sum to 100"):
        run_weight_sensitivity([company], {"bad": {k: Decimal(10) for k in KEYS}})


def test_incomplete_company_dimension_set_is_rejected():
    company = CalibrationCompany("A", {k: Decimal(70) for k in KEYS[:-1]})
    with pytest.raises(ValueError, match="exactly five"):
        run_weight_sensitivity([company], {"equal": EQUAL})
