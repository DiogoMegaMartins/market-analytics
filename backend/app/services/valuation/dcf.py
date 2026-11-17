"""Deterministic FCFF DCF valuation primitives (v1).

All monetary inputs must use the same currency and scale. This module does not
fetch market data, infer assumptions, or make investment recommendations.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any

VALUATION_VERSION = "fcff-dcf-v1"
SCENARIOS = ("BEAR", "BASE", "BULL")
ZERO = Decimal(0)
ONE = Decimal(1)


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a valid decimal") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    return result


def _periods(values: Sequence[Mapping[str, Any]], *, base_year: int, scenario: str) -> list[dict]:
    if not 1 <= len(values) <= 10:
        raise ValueError(f"{scenario} must contain between 1 and 10 forecast periods")
    result = []
    for index, item in enumerate(values, start=1):
        year = item.get("year")
        if year != base_year + index:
            raise ValueError(f"{scenario} forecast years must be consecutive from base_year + 1")
        period = {
            "year": year,
            "revenue": _decimal(item.get("revenue"), f"{scenario}.{year}.revenue"),
            "ebit_margin": _decimal(item.get("ebit_margin"), f"{scenario}.{year}.ebit_margin"),
            "tax_rate": _decimal(item.get("tax_rate"), f"{scenario}.{year}.tax_rate"),
            "da": _decimal(item.get("da"), f"{scenario}.{year}.da"),
            "capex": _decimal(item.get("capex"), f"{scenario}.{year}.capex"),
            "change_nwc": _decimal(item.get("change_nwc"), f"{scenario}.{year}.change_nwc"),
        }
        if period["revenue"] < ZERO:
            raise ValueError(f"{scenario}.{year}.revenue cannot be negative")
        if not ZERO <= period["tax_rate"] <= ONE:
            raise ValueError(f"{scenario}.{year}.tax_rate must be between 0 and 1")
        if period["da"] < ZERO or period["capex"] < ZERO:
            raise ValueError(f"{scenario}.{year}.da and capex must be non-negative magnitudes")
        result.append(period)
    return result


def _value_scenario(
    periods: list[dict], *, wacc: Decimal, terminal_growth: Decimal,
    net_debt: Decimal, diluted_shares: Decimal,
) -> dict:
    fcffs = []
    discounted_fcffs = []
    for index, period in enumerate(periods, start=1):
        ebit = period["revenue"] * period["ebit_margin"]
        nopat = ebit * (ONE - period["tax_rate"])
        fcff = nopat + period["da"] - period["capex"] - period["change_nwc"]
        discount_factor = (ONE + wacc) ** index
        fcffs.append((period["year"], fcff))
        discounted_fcffs.append(fcff / discount_factor)

    terminal_fcff = fcffs[-1][1] * (ONE + terminal_growth)
    terminal_value = terminal_fcff / (wacc - terminal_growth)
    pv_terminal_value = terminal_value / ((ONE + wacc) ** len(periods))
    pv_explicit = sum(discounted_fcffs, ZERO)
    enterprise_value = pv_explicit + pv_terminal_value
    equity_value = enterprise_value - net_debt
    value_per_share = equity_value / diluted_shares
    terminal_share = pv_terminal_value / enterprise_value if enterprise_value > ZERO else None
    return {
        "fcff_by_year": [{"year": year, "fcff": str(value)} for year, value in fcffs],
        "present_value_explicit_fcff": str(pv_explicit),
        "terminal_value": str(terminal_value),
        "present_value_terminal_value": str(pv_terminal_value),
        "enterprise_value": str(enterprise_value),
        "net_debt": str(net_debt),
        "equity_value": str(equity_value),
        "diluted_shares": str(diluted_shares),
        "value_per_share": str(value_per_share),
        "terminal_value_share_of_ev": str(terminal_share) if terminal_share is not None else None,
        "warnings": (
            ["PRESENT_VALUE_TERMINAL_VALUE_EXCEEDS_80_PERCENT_OF_EV"]
            if terminal_share is not None and terminal_share > Decimal("0.80") else []
        ),
    }


def calculate_fcff_dcf(
    *,
    base_year: int,
    currency: str,
    scenarios: Mapping[str, Sequence[Mapping[str, Any]]],
    wacc: Any,
    terminal_growth: Any,
    net_debt: Any,
    diluted_shares: Any,
) -> dict:
    """Calculate Bear/Base/Bull FCFF DCF scenarios and a Base-case sensitivity grid."""
    if not isinstance(base_year, int) or not 1900 <= base_year <= 2200:
        raise ValueError("base_year must be between 1900 and 2200")
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha() or currency.upper() != currency:
        raise ValueError("currency must be a three-letter uppercase currency code")
    if set(scenarios) != set(SCENARIOS):
        raise ValueError("scenarios must contain exactly BEAR, BASE, and BULL")
    discount_rate = _decimal(wacc, "wacc")
    growth_rate = _decimal(terminal_growth, "terminal_growth")
    debt = _decimal(net_debt, "net_debt")
    shares = _decimal(diluted_shares, "diluted_shares")
    if not ZERO < discount_rate < ONE:
        raise ValueError("wacc must be greater than 0 and less than 1")
    if growth_rate <= Decimal(-1) or growth_rate >= discount_rate:
        raise ValueError("terminal_growth must be greater than -1 and lower than wacc")
    if shares <= ZERO:
        raise ValueError("diluted_shares must be positive")

    with localcontext() as context:
        context.prec = 28
        parsed = {
            name: _periods(scenarios[name], base_year=base_year, scenario=name)
            for name in SCENARIOS
        }
        year_sets = {tuple(item["year"] for item in values) for values in parsed.values()}
        if len(year_sets) != 1:
            raise ValueError("BEAR, BASE, and BULL scenarios must use identical forecast years")
        results = {
            name: _value_scenario(
                values, wacc=discount_rate, terminal_growth=growth_rate,
                net_debt=debt, diluted_shares=shares,
            )
            for name, values in parsed.items()
        }
        wacc_steps = (Decimal("-0.01"), ZERO, Decimal("0.01"))
        growth_steps = (Decimal("-0.005"), ZERO, Decimal("0.005"))
        sensitivity = []
        for adjusted_wacc in (discount_rate + step for step in wacc_steps):
            row = {"wacc": str(adjusted_wacc), "values_per_share": []}
            for adjusted_growth in (growth_rate + step for step in growth_steps):
                if adjusted_wacc <= ZERO or adjusted_wacc >= ONE or adjusted_growth >= adjusted_wacc or adjusted_growth <= Decimal("-1"):
                    value = None
                else:
                    case = _value_scenario(
                        parsed["BASE"], wacc=adjusted_wacc,
                        terminal_growth=adjusted_growth, net_debt=debt,
                        diluted_shares=shares,
                    )
                    value = case["value_per_share"]
                row["values_per_share"].append({
                    "terminal_growth": str(adjusted_growth), "value_per_share": value,
                })
            sensitivity.append(row)

    return {
        "valuation_version": VALUATION_VERSION,
        "method": "FCFF_DCF",
        "base_year": base_year,
        "currency": currency,
        "wacc": str(discount_rate),
        "terminal_growth": str(growth_rate),
        "scenarios": results,
        "sensitivity": sensitivity,
        "analyst_review_required": True,
        "investment_recommendation": None,
        "limitations": [
            "All monetary inputs must use the same currency and scale.",
            "Forecast drivers and capital structure are explicit caller-supplied assumptions.",
            "No live market price, peer multiple, or external data is retrieved.",
            "A high terminal-value contribution is a warning, not an automatic rejection.",
            "This DCF implementation is not suitable for banks, insurers, REITs, or other sectors requiring specialist methods.",
        ],
    }
