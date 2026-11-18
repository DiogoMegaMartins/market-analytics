"""Deterministic portfolio holdings and ledger-cash reconciliation."""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

CASH_SIGNS = {
    "BUY": -1,
    "SELL": 1,
    "DIVIDEND": 1,
    "DEPOSIT": 1,
    "WITHDRAWAL": -1,
    "FEE": -1,
    "TAX": -1,
    "INTEREST": 1,
}


def _decimal(value: Any) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("portfolio ledger values must be finite")
    return result


def _value(transaction: Mapping[str, Any], key: str) -> Any:
    return transaction[key] if key in transaction else None


def build_portfolio_position_snapshot(
    transactions: Sequence[Mapping[str, Any]],
    *,
    as_of: date,
) -> dict[str, Any]:
    """Derive share quantities and cash balances from immutable ledger entries.

    Holdings use trade date. Cash has both trade-date and settlement-date views;
    a missing settlement date falls back to trade date. No cost-basis or P&L
    method is inferred.
    """
    positions: dict[str, dict[str, Decimal]] = defaultdict(
        lambda: {
            "quantity": Decimal(0),
            "bought_quantity": Decimal(0),
            "sold_quantity": Decimal(0),
            "buy_gross": Decimal(0),
            "sell_gross": Decimal(0),
        }
    )
    trade_cash = Decimal(0)
    settled_cash = Decimal(0)
    inflows = Decimal(0)
    outflows = Decimal(0)
    movements: dict[str, Decimal] = defaultdict(Decimal)
    included = 0

    for transaction in transactions:
        trade_date = _value(transaction, "trade_date")
        if trade_date > as_of:
            continue
        transaction_type = str(_value(transaction, "transaction_type"))
        if transaction_type not in CASH_SIGNS:
            raise ValueError(f"unsupported portfolio transaction type: {transaction_type}")
        gross = _decimal(_value(transaction, "gross_amount"))
        fees = _decimal(_value(transaction, "fees") or 0)
        taxes = _decimal(_value(transaction, "taxes") or 0)
        sign = CASH_SIGNS[transaction_type]
        if transaction_type == "BUY":
            cash_effect = -(gross + fees + taxes)
        elif transaction_type in {"SELL", "DIVIDEND", "INTEREST"}:
            cash_effect = gross - fees - taxes
        elif transaction_type in {"DEPOSIT", "WITHDRAWAL"}:
            cash_effect = gross * sign
        else:
            cash_effect = -(gross + fees + taxes)

        trade_cash += cash_effect
        cash_date = _value(transaction, "settlement_date") or trade_date
        if cash_date <= as_of:
            settled_cash += cash_effect
        if cash_effect >= 0:
            inflows += cash_effect
        else:
            outflows += abs(cash_effect)
        movements[transaction_type] += cash_effect
        included += 1

        if transaction_type in {"BUY", "SELL"}:
            asset_id = str(_value(transaction, "asset_id"))
            quantity = _decimal(_value(transaction, "quantity"))
            position = positions[asset_id]
            if transaction_type == "BUY":
                position["quantity"] += quantity
                position["bought_quantity"] += quantity
                position["buy_gross"] += gross
            else:
                position["quantity"] -= quantity
                position["sold_quantity"] += quantity
                position["sell_gross"] += gross

    position_rows = []
    negative_positions = []
    for asset_id in sorted(positions):
        item = positions[asset_id]
        if item["quantity"] == 0:
            continue
        negative = item["quantity"] < 0
        if negative:
            negative_positions.append(asset_id)
        position_rows.append({
            "asset_id": asset_id,
            "quantity": str(item["quantity"]),
            "bought_quantity": str(item["bought_quantity"]),
            "sold_quantity": str(item["sold_quantity"]),
            "buy_gross": str(item["buy_gross"]),
            "sell_gross": str(item["sell_gross"]),
            "negative_position": negative,
        })

    return {
        "as_of": as_of.isoformat(),
        "transaction_count": included,
        "positions": position_rows,
        "cash_reconciliation": {
            "trade_date_balance": str(trade_cash),
            "settled_balance": str(settled_cash),
            "unsettled_net_amount": str(trade_cash - settled_cash),
            "inflows": str(inflows),
            "outflows": str(outflows),
            "net_movements_by_type": {
                key: str(movements[key]) for key in sorted(movements)
            },
        },
        "reconciliation": {
            "negative_position_asset_ids": negative_positions,
            "negative_position_count": len(negative_positions),
            "status": "REVIEW_REQUIRED" if negative_positions else "BALANCED",
            "limitations": [
                "Positions are net quantities derived from BUY and SELL trade dates.",
                "Cash is derived from ledger entries, not reconciled to a broker or bank statement.",
                "Settlement cash uses settlement_date, falling back to trade_date when absent.",
                "No lot accounting, cost basis, realized/unrealized P&L, FX, or corporate actions are applied.",
                "A negative position is flagged for review; it is not automatically corrected.",
            ],
        },
    }
