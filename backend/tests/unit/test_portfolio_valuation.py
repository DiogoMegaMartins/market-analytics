from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.v1.endpoints.portfolio_valuation import PortfolioValuationCreate


def _payload(**changes):
    value = {
        "valuation_date": date(2026, 1, 31), "market_value": "1250.50",
        "cash_value": "250.00", "currency": "EUR", "valuation_source": "MANUAL",
        "methodology": "Broker statement marked to market", "idempotency_key": "valuation-2026-01",
    }
    value.update(changes)
    return value


def test_valuation_input_accepts_nonnegative_finite_values():
    item = PortfolioValuationCreate.model_validate(_payload())
    assert item.market_value + item.cash_value == Decimal("1500.50")


@pytest.mark.parametrize("field,value", [("market_value", "-1"), ("cash_value", "-0.01"), ("market_value", "NaN"), ("cash_value", "Infinity")])
def test_valuation_values_must_be_nonnegative_and_finite(field, value):
    with pytest.raises(ValidationError):
        PortfolioValuationCreate.model_validate(_payload(**{field: value}))


def test_valuation_source_and_currency_are_constrained():
    with pytest.raises(ValidationError):
        PortfolioValuationCreate.model_validate(_payload(valuation_source="ESTIMATE"))
    with pytest.raises(ValidationError):
        PortfolioValuationCreate.model_validate(_payload(currency="EURO"))


def test_methodology_cannot_be_blank():
    with pytest.raises(ValidationError):
        PortfolioValuationCreate.model_validate(_payload(methodology="   "))
