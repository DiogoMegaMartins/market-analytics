from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.v1.endpoints.valuation import DCFValuationInput, router
from app.models import Base


def _period(year: int) -> dict:
    return {
        "year": year, "revenue": "1000", "ebit_margin": "0.2",
        "tax_rate": "0.25", "da": "40", "capex": "50", "change_nwc": "10",
    }


def _payload() -> dict:
    return {
        "base_year": 2024, "currency": "USD", "wacc": "0.09",
        "terminal_growth": "0.025", "net_debt": "100", "diluted_shares": "50",
        "scenarios": {
            "BEAR": [_period(2025)], "BASE": [_period(2025)], "BULL": [_period(2025)],
        },
    }


def test_valuation_routes_are_company_scoped_and_registered():
    paths = {route.path for route in router.routes}
    assert "/valuation/companies/{company_id}/dcf" in paths
    assert "/valuation/companies/{company_id}/history" in paths
    assert any(getattr(dep.dependency, "__name__", "") == "require_company_access"
               for dep in router.dependencies)


def test_valuation_input_rejects_unknown_fields():
    payload = _payload()
    payload["unexpected"] = True
    with pytest.raises(ValidationError):
        DCFValuationInput.model_validate(payload)


def test_valuation_input_preserves_explicit_scenario_assumptions():
    payload = DCFValuationInput.model_validate(_payload())
    assert payload.scenarios["BASE"][0].revenue == 1000
    assert payload.wacc == Decimal("0.09")


def test_valuation_run_table_is_registered_for_migrations():
    table = Base.metadata.tables["valuation_runs"]
    assert {"company_id", "created_by_user_id", "assumptions", "result"} <= set(table.columns.keys())
