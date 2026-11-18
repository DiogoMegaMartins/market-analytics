from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.v1.endpoints.portfolio import PortfolioTransactionCreate


def _payload(**overrides):
    values = {
        "transaction_type": "BUY",
        "trade_date": date(2026, 1, 5),
        "asset_id": uuid4(),
        "quantity": "2.5",
        "unit_price": "10.00",
        "gross_amount": "25.00",
        "currency": "USD",
        "idempotency_key": "broker-transaction-001",
    }
    values.update(overrides)
    return values


def test_buy_transaction_requires_matching_positive_quantity_and_price():
    item = PortfolioTransactionCreate.model_validate(_payload())
    assert item.gross_amount == Decimal("25.00")
    with pytest.raises(ValidationError):
        PortfolioTransactionCreate.model_validate(_payload(gross_amount="24.99"))
    with pytest.raises(ValidationError):
        PortfolioTransactionCreate.model_validate(_payload(quantity="0"))


def test_sell_transaction_has_same_shape_as_buy():
    item = PortfolioTransactionCreate.model_validate(_payload(transaction_type="SELL"))
    assert item.transaction_type == "SELL"


@pytest.mark.parametrize("transaction_type", ["DEPOSIT", "WITHDRAWAL", "INTEREST"])
def test_cash_transactions_do_not_reference_assets(transaction_type):
    item = PortfolioTransactionCreate.model_validate(_payload(
        transaction_type=transaction_type, asset_id=None, quantity=None,
        unit_price=None, gross_amount="100.00",
    ))
    assert item.asset_id is None


def test_dividend_requires_an_asset():
    with pytest.raises(ValidationError):
        PortfolioTransactionCreate.model_validate(_payload(
            transaction_type="DIVIDEND", asset_id=None, quantity=None,
            unit_price=None, gross_amount="2.50",
        ))


def test_settlement_date_cannot_precede_trade_date():
    with pytest.raises(ValidationError):
        PortfolioTransactionCreate.model_validate(_payload(
            settlement_date=date(2026, 1, 4),
        ))


def test_fees_and_taxes_must_be_nonnegative_and_finite():
    with pytest.raises(ValidationError):
        PortfolioTransactionCreate.model_validate(_payload(fees="-0.01"))
    with pytest.raises(ValidationError):
        PortfolioTransactionCreate.model_validate(_payload(taxes="NaN"))
