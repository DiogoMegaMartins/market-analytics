"""Relative performance calculation for portfolio TWR and total-return indices."""
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any


def _positive_decimal(value: Any, label: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a valid decimal") from exc
    if not result.is_finite() or result <= 0:
        raise ValueError(f"{label} must be finite and positive")
    return result


def calculate_relative_performance(
    *,
    portfolio_twr: Any,
    benchmark_start_level: Any,
    benchmark_end_level: Any,
    start_date: date,
    end_date: date,
    portfolio_currency: str,
    benchmark_currency: str,
) -> dict[str, str]:
    """Compare period TWR with a same-currency total-return index over identical dates."""
    if end_date <= start_date:
        raise ValueError("end_date must be after start_date")
    if portfolio_currency != benchmark_currency:
        raise ValueError("portfolio and benchmark currencies must match; FX conversion is not supported")
    try:
        portfolio_return = Decimal(str(portfolio_twr))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("portfolio_twr must be a valid decimal") from exc
    if not portfolio_return.is_finite():
        raise ValueError("portfolio_twr must be finite")
    start_level = _positive_decimal(benchmark_start_level, "benchmark_start_level")
    end_level = _positive_decimal(benchmark_end_level, "benchmark_end_level")
    with localcontext() as context:
        context.prec = 28
        benchmark_return = end_level / start_level - Decimal(1)
        excess_return = portfolio_return - benchmark_return
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "currency": portfolio_currency,
        "portfolio_twr": str(portfolio_return),
        "portfolio_twr_percent": str(portfolio_return * Decimal(100)),
        "benchmark_total_return": str(benchmark_return),
        "benchmark_total_return_percent": str(benchmark_return * Decimal(100)),
        "relative_return": str(excess_return),
        "relative_return_percentage_points": str(excess_return * Decimal(100)),
    }
