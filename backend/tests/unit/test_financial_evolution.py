from decimal import Decimal

import pytest

from app.services.metrics.evolution import build_financial_evolution


def _metric(metric_id, value, unit="USD", status="CALCULATED"):
    return {"metric_id": metric_id, "value": value, "unit": unit, "status": status}


def test_financial_evolution_flags_material_growth():
    result = build_financial_evolution(
        company_id="company-1", from_fiscal_year=2023, to_fiscal_year=2024,
        previous_metrics=[_metric("FIN.REVENUE", "1000")],
        current_metrics=[_metric("FIN.REVENUE", "1200")],
    )
    row = result["metrics"][0]
    assert row["absolute_change"] == "200"
    assert row["percentage_change"] == "20.0"
    assert row["materiality"] == "MATERIAL"
    assert result["summary"]["material_changes"] == 1
    assert result["interpretation"]["thesis_status_changed"] is False


def test_financial_evolution_marks_small_move_non_material():
    result = build_financial_evolution(
        company_id="c", from_fiscal_year=2023, to_fiscal_year=2024,
        previous_metrics=[_metric("FIN.REVENUE", "100")],
        current_metrics=[_metric("FIN.REVENUE", "105")],
    )
    assert result["metrics"][0]["materiality"] == "NON_MATERIAL"


def test_financial_evolution_blocks_unit_mismatch():
    result = build_financial_evolution(
        company_id="c", from_fiscal_year=2023, to_fiscal_year=2024,
        previous_metrics=[_metric("FIN.REVENUE", "100", "USD")],
        current_metrics=[_metric("FIN.REVENUE", "105", "EUR")],
    )
    assert result["metrics"][0]["materiality"] == "REVIEW_REQUIRED"
    assert result["metrics"][0]["absolute_change"] is None


def test_financial_evolution_does_not_compare_unavailable_metrics():
    result = build_financial_evolution(
        company_id="c", from_fiscal_year=2023, to_fiscal_year=2024,
        previous_metrics=[_metric("FIN.FCF", "100", status="CALCULATED")],
        current_metrics=[_metric("FIN.FCF", None, status="UNAVAILABLE")],
    )
    assert result["metrics"][0]["materiality"] == "NOT_ASSESSED"


def test_financial_evolution_flags_nonpositive_base_for_review():
    result = build_financial_evolution(
        company_id="c", from_fiscal_year=2023, to_fiscal_year=2024,
        previous_metrics=[_metric("FIN.FCF", "-10")],
        current_metrics=[_metric("FIN.FCF", "10")],
    )
    assert result["metrics"][0]["materiality"] == "REVIEW_REQUIRED"
    assert result["metrics"][0]["percentage_change"] is None


def test_financial_evolution_identifies_metrics_missing_from_one_period():
    result = build_financial_evolution(
        company_id="c", from_fiscal_year=2023, to_fiscal_year=2024,
        previous_metrics=[_metric("FIN.REVENUE", "100")],
        current_metrics=[],
    )
    assert result["metrics"][0]["materiality"] == "NOT_ASSESSED"


def test_financial_evolution_rejects_invalid_period_and_threshold():
    with pytest.raises(ValueError, match="earlier"):
        build_financial_evolution(
            company_id="c", from_fiscal_year=2024, to_fiscal_year=2024,
            previous_metrics=[], current_metrics=[],
        )
    with pytest.raises(ValueError, match="threshold"):
        build_financial_evolution(
            company_id="c", from_fiscal_year=2023, to_fiscal_year=2024,
            previous_metrics=[], current_metrics=[], threshold_pct=Decimal(0),
        )


def test_financial_evolution_route_is_company_scoped():
    from app.api.v1.endpoints.metrics import router

    route = next((item for item in router.routes if getattr(item, "path", None) ==
                  "/metrics/companies/{company_id}/evolution"), None)
    assert route is not None and "GET" in route.methods
    assert any(getattr(dependency.dependency, "__name__", "") == "require_company_access"
               for dependency in router.dependencies)
