from datetime import date
from decimal import InvalidOperation

import pytest

from app.services.portfolio.positions import build_portfolio_position_snapshot


def _tx(kind, *, trade=date(2026, 1, 5), settlement=None, asset=None,
        quantity=None, gross="100", fees="0", taxes="0"):
    return {
        "transaction_type": kind,
        "trade_date": trade,
        "settlement_date": settlement,
        "asset_id": asset,
        "quantity": quantity,
        "gross_amount": gross,
        "fees": fees,
        "taxes": taxes,
    }


def test_positions_net_buys_and_sells_without_inventing_cost_basis():
    result = build_portfolio_position_snapshot([
        _tx("BUY", asset="asset-a", quantity="10", gross="100", fees="2"),
        _tx("SELL", asset="asset-a", quantity="4", gross="60", taxes="1"),
        _tx("BUY", asset="asset-b", quantity="2", gross="50"),
    ], as_of=date(2026, 1, 31))
    assert result["positions"] == [
        {"asset_id": "asset-a", "quantity": "6", "bought_quantity": "10",
         "sold_quantity": "4", "buy_gross": "100", "sell_gross": "60",
         "negative_position": False},
        {"asset_id": "asset-b", "quantity": "2", "bought_quantity": "2",
         "sold_quantity": "0", "buy_gross": "50", "sell_gross": "0",
         "negative_position": False},
    ]
    assert result["reconciliation"]["status"] == "BALANCED"


def test_negative_position_is_flagged_and_not_silently_clamped():
    result = build_portfolio_position_snapshot([
        _tx("SELL", asset="asset-a", quantity="3", gross="30"),
    ], as_of=date(2026, 1, 31))
    assert result["positions"][0]["quantity"] == "-3"
    assert result["reconciliation"]["negative_position_asset_ids"] == ["asset-a"]
    assert result["reconciliation"]["status"] == "REVIEW_REQUIRED"


def test_cash_reconciliation_accounts_for_fees_taxes_and_settlement():
    result = build_portfolio_position_snapshot([
        _tx("DEPOSIT", gross="500"),
        _tx("BUY", asset="asset-a", quantity="2", gross="200",
            fees="3", settlement=date(2026, 2, 2)),
        _tx("DIVIDEND", asset="asset-a", gross="5", taxes="1"),
        _tx("FEE", gross="2"),
    ], as_of=date(2026, 1, 31))
    cash = result["cash_reconciliation"]
    assert cash["trade_date_balance"] == "299"
    assert cash["settled_balance"] == "502"
    assert cash["unsettled_net_amount"] == "-203"
    assert cash["inflows"] == "504"
    assert cash["outflows"] == "205"


def test_transactions_after_cutoff_are_excluded():
    result = build_portfolio_position_snapshot([
        _tx("BUY", asset="asset-a", quantity="1", gross="10",
            trade=date(2026, 2, 1)),
    ], as_of=date(2026, 1, 31))
    assert result["transaction_count"] == 0
    assert result["positions"] == []
    assert result["cash_reconciliation"]["trade_date_balance"] == "0"


def test_rejects_unknown_transaction_types_and_non_finite_values():
    with pytest.raises(ValueError, match="unsupported"):
        build_portfolio_position_snapshot(
            [_tx("SPLIT", asset="asset-a", quantity="2")],
            as_of=date(2026, 1, 31),
        )
    with pytest.raises(InvalidOperation):
        build_portfolio_position_snapshot(
            [_tx("DEPOSIT", gross="NaN")],
            as_of=date(2026, 1, 31),
        )
