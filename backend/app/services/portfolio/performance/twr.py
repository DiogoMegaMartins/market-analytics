"""Daily-boundary time-weighted portfolio return calculation.

External flows are treated as occurring at the start of their trade date.
A dated valuation is therefore required on each external-flow date.
"""
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any


def _decimal(value: Any, label: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a valid decimal") from exc
    if not result.is_finite():
        raise ValueError(f"{label} must be finite")
    return result


def _date(value: Any, label: str) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be an ISO date") from exc


def calculate_time_weighted_return(
    valuations: Sequence[Mapping[str, Any]],
    external_cash_flows: Sequence[Mapping[str, Any]],
    *,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    """Calculate geometrically linked subperiod returns.

    Cash-flow amounts use investor perspective: deposits positive, withdrawals
    negative. Flows are assumed to occur at the start of their trade date.
    For every flow date in (start_date, end_date], a valuation on that exact
    date is mandatory. The latest recorded observation on a date is canonical;
    ties are resolved by lexicographically greatest id.
    """
    if end_date <= start_date:
        raise ValueError("end_date must be after start_date")

    canonical: dict[date, tuple[tuple[str, str], Decimal]] = {}
    for item in valuations:
        observed = _date(item.get("valuation_date"), "valuation_date")
        if observed < start_date or observed > end_date:
            continue
        value = _decimal(item.get("total_value"), "total_value")
        if value < 0:
            raise ValueError("valuation total_value cannot be negative")
        recorded = str(item.get("recorded_at") or "")
        identifier = str(item.get("id") or "")
        rank = (recorded, identifier)
        if observed not in canonical or rank > canonical[observed][0]:
            canonical[observed] = (rank, value)

    if start_date not in canonical:
        raise ValueError("a starting valuation is required on start_date")
    if end_date not in canonical:
        raise ValueError("an ending valuation is required on end_date")

    flows: dict[date, Decimal] = defaultdict(Decimal)
    flow_count = 0
    for item in external_cash_flows:
        flow_date = _date(item.get("flow_date"), "flow_date")
        if flow_date <= start_date or flow_date > end_date:
            continue
        flow_type = str(item.get("flow_type"))
        amount = _decimal(item.get("amount"), "external cash flow amount")
        if amount <= 0:
            raise ValueError("external cash flow amount must be positive")
        if flow_type == "DEPOSIT":
            flows[flow_date] += amount
        elif flow_type == "WITHDRAWAL":
            flows[flow_date] -= amount
        else:
            raise ValueError(f"unsupported external cash flow type: {flow_type}")
        flow_count += 1

    flow_dates = sorted(day for day, amount in flows.items() if amount != 0)
    valuation_dates = sorted(canonical)
    linked_factors: list[Decimal] = []
    subperiods: list[dict[str, str]] = []
    period_start = start_date
    start_value = canonical[start_date][1]

    for flow_date in flow_dates:
        if flow_date not in canonical:
            raise ValueError(f"a valuation is required on external cash-flow date {flow_date.isoformat()}")
        prior_dates = [day for day in valuation_dates if period_start <= day < flow_date]
        if not prior_dates:
            raise ValueError(f"a valuation before external cash-flow date {flow_date.isoformat()} is required")
        prior_date = max(prior_dates)
        prior_value = canonical[prior_date][1]
        if start_value <= 0:
            raise ValueError(f"non-positive starting capital before {flow_date.isoformat()}")
        with localcontext() as context:
            context.prec = 28
            pre_flow_factor = prior_value / start_value
            pre_flow_return = pre_flow_factor - Decimal(1)
        linked_factors.append(pre_flow_factor)
        subperiods.append({
            "start_date": period_start.isoformat(),
            "end_date": prior_date.isoformat(),
            "start_value": str(start_value),
            "external_cash_flow": "0",
            "end_value": str(prior_value),
            "return": str(pre_flow_return),
        })

        adjusted_capital = prior_value + flows[flow_date]
        if adjusted_capital <= 0:
            raise ValueError(f"non-positive invested capital after external flow on {flow_date.isoformat()}")
        ending_value = canonical[flow_date][1]
        with localcontext() as context:
            context.prec = 28
            post_flow_factor = ending_value / adjusted_capital
            post_flow_return = post_flow_factor - Decimal(1)
        linked_factors.append(post_flow_factor)
        subperiods.append({
            "start_date": prior_date.isoformat(),
            "end_date": flow_date.isoformat(),
            "start_value": str(adjusted_capital),
            "external_cash_flow": str(flows[flow_date]),
            "end_value": str(ending_value),
            "return": str(post_flow_return),
        })
        period_start = flow_date
        start_value = ending_value

    final_date = end_date
    final_value = canonical[final_date][1]
    if start_value <= 0:
        raise ValueError("starting portfolio value for final subperiod must be positive")
    with localcontext() as context:
        context.prec = 28
        final_factor = final_value / start_value
        final_return = final_factor - Decimal(1)
    linked_factors.append(final_factor)
    subperiods.append({
        "start_date": period_start.isoformat(),
        "end_date": final_date.isoformat(),
        "start_value": str(start_value),
        "external_cash_flow": "0",
        "end_value": str(final_value),
        "return": str(final_return),
    })


    with localcontext() as context:
        context.prec = 28
        cumulative_factor = Decimal(1)
        for factor in linked_factors:
            cumulative_factor *= factor
        total_return = cumulative_factor - Decimal(1)

    return {
        "method": "TWR_START_OF_DAY_EXTERNAL_FLOWS",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "starting_value": str(canonical[start_date][1]),
        "ending_value": str(canonical[end_date][1]),
        "external_cash_flow_count": flow_count,
        "net_external_cash_flows": str(sum(flows.values(), Decimal(0))),
        "subperiod_count": len(subperiods),
        "subperiods": subperiods,
        "time_weighted_return": str(total_return),
        "time_weighted_return_percent": str(total_return * Decimal(100)),
        "coverage_status": "COMPLETE",
        "limitations": [
            "External cash flows are assumed to occur at the start of their trade date.",
            "A valuation is required on each date with a non-zero net external cash flow.",
            "The latest recorded valuation on each date is selected; ties use the greatest snapshot id.",
            "Valuations are supplied observations and are not independently verified NAV.",
            "No FX, benchmark, fees outside portfolio valuation, or MWR/XIRR calculation is applied.",
        ],
    }
