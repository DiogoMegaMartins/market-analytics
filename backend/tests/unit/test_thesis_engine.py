import pytest
from pydantic import ValidationError

from app.services.thesis.evaluation import evaluate_thesis_assumptions


def assumption(condition="BELOW", threshold="10", unit="ratio"):
    return {
        "assumption_id": "margin-floor",
        "description": "Operating margin should remain above 10%",
        "metric_id": "FIN.OPERATING_MARGIN",
        "condition": condition,
        "threshold": threshold,
        "unit": unit,
    }


def test_thesis_assumption_detects_breach_candidate():
    result = evaluate_thesis_assumptions(
        assumptions=[assumption("BELOW", "0.10")],
        metrics=[{"metric_id": "FIN.OPERATING_MARGIN", "value": "0.07",
                  "unit": "ratio", "status": "CALCULATED"}],
        fiscal_year=2024,
    )
    assert result["overall_status"] == "BREACH_CANDIDATE"
    assert result["assumption_evaluations"][0]["status"] == "BREACH_CANDIDATE"
    assert result["automatic_invalidation"] is False


def test_thesis_assumption_no_breach():
    result = evaluate_thesis_assumptions(
        assumptions=[assumption("BELOW", "0.10")],
        metrics=[{"metric_id": "FIN.OPERATING_MARGIN", "value": "0.15",
                  "unit": "ratio", "status": "CALCULATED"}],
        fiscal_year=2024,
    )
    assert result["overall_status"] == "NO_BREACH_DETECTED"


def test_thesis_assumption_missing_metric_is_unknown_not_breach():
    result = evaluate_thesis_assumptions(
        assumptions=[assumption()], metrics=[], fiscal_year=2024,
    )
    assert result["overall_status"] == "INSUFFICIENT_DATA"
    assert result["assumption_evaluations"][0]["status"] == "UNKNOWN"


def test_thesis_assumption_unit_mismatch_requires_review():
    result = evaluate_thesis_assumptions(
        assumptions=[assumption()],
        metrics=[{"metric_id": "FIN.OPERATING_MARGIN", "value": "0.05",
                  "unit": "percent", "status": "CALCULATED"}],
        fiscal_year=2024,
    )
    assert result["overall_status"] == "REVIEW_REQUIRED"


def test_thesis_assumption_only_calculated_metrics_are_used():
    result = evaluate_thesis_assumptions(
        assumptions=[assumption()],
        metrics=[{"metric_id": "FIN.OPERATING_MARGIN", "value": "0.01",
                  "unit": "ratio", "status": "UNAVAILABLE"}],
        fiscal_year=2024,
    )
    assert result["overall_status"] == "INSUFFICIENT_DATA"


def test_thesis_above_condition():
    result = evaluate_thesis_assumptions(
        assumptions=[assumption("ABOVE", "100", "USD")],
        metrics=[{"metric_id": "FIN.OPERATING_MARGIN", "value": "120",
                  "unit": "USD", "status": "CALCULATED"}],
        fiscal_year=2024,
    )
    assert result["overall_status"] == "BREACH_CANDIDATE"


def test_thesis_empty_assumptions_is_insufficient():
    result = evaluate_thesis_assumptions(assumptions=[], metrics=[], fiscal_year=2024)
    assert result["overall_status"] == "INSUFFICIENT_DATA"


def test_thesis_routes_are_registered_and_company_scoped():
    from app.api.v1.endpoints.thesis import router

    paths = {route.path for route in router.routes}
    assert "/thesis/companies/{company_id}/theses" in paths
    assert "/thesis/{thesis_id}/evaluate" in paths
    assert "/thesis/{thesis_id}/decisions" in paths
    assert any(getattr(dep.dependency, "__name__", "") == "require_company_access"
               for dep in router.dependencies)


def test_company_access_dependency_resolves_thesis_company():
    from pathlib import Path
    source = Path("app/api/v1/dependencies.py").read_text()
    assert '"thesis_id"' in source
    assert "InvestmentThesis" in source


def test_thesis_evidence_routes_are_registered():
    from app.api.v1.endpoints.thesis import router
    paths = {route.path for route in router.routes}
    assert "/thesis/{thesis_id}/evidence-links" in paths
    assert "/thesis/{thesis_id}/intelligence" in paths


def test_thesis_evidence_model_enforces_single_source_and_relationship():
    from app.models.thesis_evidence import InvestmentThesisEvidenceLink
    constraints = {constraint.name: str(constraint.sqltext)
                   for constraint in InvestmentThesisEvidenceLink.__table__.constraints
                   if getattr(constraint, "sqltext", None) is not None}
    assert any(name.endswith("ck_thesis_evidence_exactly_one_target") for name in constraints)
    assert any(name.endswith("ck_thesis_evidence_relationship") for name in constraints)


def test_thesis_evidence_payload_rejects_unknown_relationship():
    from uuid import uuid4

    from app.api.v1.endpoints.thesis import ThesisEvidenceLinkInput

    with pytest.raises(ValidationError):
        ThesisEvidenceLinkInput(assumption_id="a", metric_result_id=uuid4(),
                                relationship="PROVES", rationale="test")


def test_thesis_evidence_model_is_in_alembic_registry():
    from app.models import Base
    assert "investment_thesis_evidence_links" in Base.metadata.tables
