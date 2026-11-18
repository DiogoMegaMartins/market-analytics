"""Money-weighted portfolio return (XIRR) from dated NAV and investor cash flows.

Investor perspective: contributions/deposits are negative; withdrawals/distributions
and terminal portfolio NAV are positive. Actual/365 day-count is used.
"""
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal, InvalidOperation
import math
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


def _npv(log_rate: float, dated_amounts: list[tuple[int, float]]) -> float:
    return math.fsum(
        amount * math.exp(max(-700.0, min(700.0, -log_rate * (days / 365.0))))
        for days, amount in dated_amounts
    )


def _bisect_root(
    left: float,
    right: float,
    left_value: float,
    dated_amounts: list[tuple[int, float]],
    *,
    tolerance: float,
) -> float:
    for _ in range(256):
        middle = (left + right) / 2.0
        middle_value = _npv(middle, dated_amounts)
        if abs(middle_value) <= tolerance or abs(right - left) <= 1e-13:
            return middle
        if (left_value < 0) == (middle_value < 0):
            left, left_value = middle, middle_value
        else:
            right = middle
    return (left + right) / 2.0


def _solve_xirr(dated_amounts: list[tuple[int, float]]) -> tuple[float, int]:
    positive = any(amount > 0 for _, amount in dated_amounts)
    negative = any(amount < 0 for _, amount in dated_amounts)
    if not positive or not negative:
        raise ValueError("XIRR requires at least one positive and one negative investor cash flow")

    scale = max(abs(amount) for _, amount in dated_amounts)
    tolerance = max(scale * 1e-12, 1e-12)
    # Search in log(1 + rate) space, covering rates from -99.99% to 100,000%.
    low, high, steps = math.log(0.0001), math.log(1001.0), 8192
    roots: list[float] = []
    previous_x = low
    previous_y = _npv(previous_x, dated_amounts)
    if abs(previous_y) <= tolerance:
        roots.append(previous_x)

    for index in range(1, steps + 1):
        current_x = low + (high - low) * index / steps
        current_y = _npv(current_x, dated_amounts)
        if abs(current_y) <= tolerance:
            roots.append(current_x)
        elif math.isfinite(previous_y) and math.isfinite(current_y) and (previous_y < 0) != (current_y < 0):
            roots.append(_bisect_root(previous_x, current_x, previous_y, dated_amounts, tolerance=tolerance))
        previous_x, previous_y = current_x, current_y

    unique: list[float] = []
    for root in sorted(roots):
        if not unique or abs(root - unique[-1]) > 1e-7:
            unique.append(root)
    if not unique:
        raise ValueError("no XIRR root found within the supported rate range (-99.99%, 100000%)")
    if len(unique) > 1:
        raise ValueError("XIRR is ambiguous: multiple roots were found for the supplied cash flows")
    return math.expm1(unique[0]), len(unique)


def calculate_money_weighted_return(
    valuations: Sequence[Mapping[str, Any]],
    external_cash_flows: Sequence[Mapping[str, Any]],
    *,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    """Calculate annualized XIRR from start NAV, external flows and ending NAV.

    The starting NAV is an investor contribution at start_date. Deposits in
    (start_date, end_date] are negative investor flows; withdrawals are positive.
    The ending NAV is a positive terminal distribution on end_date. Latest
    recorded valuation per date is canonical, ties resolved by greatest id.
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
        rank = (str(item.get("recorded_at") or ""), str(item.get("id") or ""))
        if observed not in canonical or rank > canonical[observed][0]:
            canonical[observed] = (rank, value)

    if start_date not in canonical:
        raise ValueError("a starting valuation is required on start_date")
    if end_date not in canonical:
        raise ValueError("an ending valuation is required on end_date")
    starting_value, ending_value = canonical[start_date][1], canonical[end_date][1]
    if starting_value <= 0:
        raise ValueError("starting portfolio value must be positive")
    if ending_value <= 0:
        raise ValueError("ending portfolio value must be positive")

    flows: dict[date, Decimal] = defaultdict(Decimal)
    flow_count = 0
    for item in external_cash_flows:
        flow_date = _date(item.get("flow_date"), "flow_date")
        if flow_date <= start_date or flow_date > end_date:
            continue
        amount = _decimal(item.get("amount"), "external cash flow amount")
        if amount <= 0:
            raise ValueError("external cash flow amount must be positive")
        flow_type = str(item.get("flow_type"))
        if flow_type == "DEPOSIT":
            flows[flow_date] -= amount
        elif flow_type == "WITHDRAWAL":
            flows[flow_date] += amount
        else:
            raise ValueError(f"unsupported external cash flow type: {flow_type}")
        flow_count += 1

    dated: dict[date, Decimal] = defaultdict(Decimal)
    dated[start_date] -= starting_value
    for day, amount in flows.items():
        dated[day] += amount
    dated[end_date] += ending_value
    dated = {day: amount for day, amount in dated.items() if amount != 0}
    origin = min(dated)
    raw_amounts = [((day - origin).days, float(amount)) for day, amount in sorted(dated.items())]
    if any(not math.isfinite(amount) for _, amount in raw_amounts):
        raise ValueError("cash flows exceed the supported numeric range")
    scale = max(abs(amount) for _, amount in raw_amounts)
    dated_amounts = [(days, amount / scale) for days, amount in raw_amounts]

    rate, root_count = _solve_xirr(dated_amounts)
    if not math.isfinite(rate):
        raise ValueError("XIRR result is not finite")

    cash_flow_rows = [
        {"date": day.isoformat(), "investor_cash_flow": str(amount)}
        for day, amount in sorted(dated.items())
    ]
    return {
        "method": "XIRR_ACTUAL_365",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "day_count": "ACTUAL_365",
        "starting_value": str(starting_value),
        "ending_value": str(ending_value),
        "external_cash_flow_count": flow_count,
        "cash_flows": cash_flow_rows,
        "money_weighted_return": repr(rate),
        "money_weighted_return_percent": repr(rate * 100.0),
        "root_count": root_count,
        "coverage_status": "COMPLETE",
        "limitations": [
            "Deposits are negative investor contributions; withdrawals are positive distributions.",
            "Starting NAV is treated as an investor contribution and ending NAV as a terminal distribution.",
            "Actual/365 day-count is used; no FX conversion or benchmark comparison is applied.",
            "The latest recorded valuation per date is selected; ties use the greatest snapshot id.",
            "Valuations are supplied observations and are not independently verified NAV.",
            "Root search is bounded to annual rates from -99.99% through 100000%; multiple roots are rejected as ambiguous.",
        ],
    }
