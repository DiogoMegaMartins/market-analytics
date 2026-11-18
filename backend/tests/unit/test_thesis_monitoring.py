from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.services.thesis.evaluation import material_change


def test_material_change_is_deterministic_and_includes_exact_boundary():
    assert material_change("100", "120", threshold_percent=Decimal(20)) == {
        "previous_value": "100", "current_value": "120", "change_percent": "20",
        "threshold_percent": "20",
    }


def test_material_change_uses_absolute_baseline_and_handles_zero():
    assert material_change("-100", "-125", threshold_percent=Decimal(20))["change_percent"] == "25"
    assert material_change("0", "1", threshold_percent=Decimal(20))["change_percent"] == "UNBOUNDED_FROM_ZERO"
    assert material_change("100", "119", threshold_percent=Decimal(20)) is None


def test_invalid_and_non_finite_values_do_not_alert():
    assert material_change("not-a-number", "2", threshold_percent=Decimal(20)) is None
    assert material_change("NaN", "2", threshold_percent=Decimal(20)) is None


def test_monitoring_routes_and_models_are_registered():
    from app.api.v1.endpoints.thesis import AlertStatusInput, router
    from app.models import Base

    paths = {route.path for route in router.routes}
    assert "/thesis/{thesis_id}/monitor" in paths
    assert "/thesis/{thesis_id}/alerts" in paths
    assert "/thesis/{thesis_id}/alerts/{alert_id}" in paths
    assert "investment_thesis_alerts" in Base.metadata.tables
    assert "investment_thesis_alert_events" in Base.metadata.tables
    with pytest.raises(ValidationError):
        AlertStatusInput(status="PENDING")


def test_alert_response_exposes_metric_run_provenance_and_review_history_contract():
    from app.api.v1.endpoints.thesis import router

    route = next(route for route in router.routes if route.path == "/thesis/{thesis_id}/alerts")
    assert route.methods == {"GET"}
    # The response contract includes the persisted run metadata and each immutable
    # status transition; this test guards route registration while PostgreSQL
    # integration exercises the joined records.
    assert "metric_run" in route.endpoint.__code__.co_names or "metric_runs" in route.endpoint.__code__.co_names
    assert "history" in route.endpoint.__code__.co_names
