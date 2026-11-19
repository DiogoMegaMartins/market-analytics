from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
from enum import StrEnum

ZERO = Decimal(0)
ONE = Decimal(1)
METRICS_VERSION = "financial-metrics-v1.1"


class MetricStatus(StrEnum):
    CALCULATED = "CALCULATED"
    UNAVAILABLE = "UNAVAILABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    INVALID_INPUT = "INVALID_INPUT"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"


@dataclass(frozen=True)
class MetricValue:
    metric_id: str
    value: Decimal | None
    unit: str
    status: MetricStatus
    reason: str | None = None


def _ratio(metric_id: str, numerator: Decimal | None, denominator: Decimal | None,
           *, unit: str = "ratio") -> MetricValue:
    if numerator is None or denominator is None:
        return MetricValue(metric_id, None, unit, MetricStatus.UNAVAILABLE, "Required input missing")
    if denominator == ZERO:
        return MetricValue(metric_id, None, unit, MetricStatus.INVALID_INPUT, "Denominator is zero")
    return MetricValue(metric_id, numerator / denominator, unit, MetricStatus.CALCULATED)


def calculate_annual_metrics(inputs: Mapping[str, Decimal | None]) -> list[MetricValue]:
    """Pure, deterministic annual metrics. CAPEX must already be a positive magnitude."""
    revenue = inputs.get("FIN.REVENUE")
    gross_profit = inputs.get("FIN.GROSS_PROFIT")
    operating_income = inputs.get("FIN.OPERATING_INCOME")
    net_income = inputs.get("FIN.NET_INCOME")
    ocf = inputs.get("FIN.OCF")
    capex = inputs.get("FIN.CAPEX")

    results = [
        _ratio("FIN.GROSS_MARGIN", gross_profit, revenue),
        _ratio("FIN.OPERATING_MARGIN", operating_income, revenue),
        _ratio("FIN.NET_MARGIN", net_income, revenue),
        _ratio("FIN.OCF_MARGIN", ocf, revenue),
    ]
    if ocf is None or capex is None:
        fcf = MetricValue("FIN.FCF", None, "currency", MetricStatus.UNAVAILABLE, "OCF and CAPEX required")
        fcf_margin = MetricValue("FIN.FCF_MARGIN", None, "ratio", MetricStatus.UNAVAILABLE, "OCF and CAPEX required")
    elif capex < ZERO:
        fcf = MetricValue("FIN.FCF", None, "currency", MetricStatus.INVALID_INPUT,
                          "CAPEX must be a positive magnitude; sign normalization is not configured")
        fcf_margin = MetricValue("FIN.FCF_MARGIN", None, "ratio", MetricStatus.INVALID_INPUT,
                                 "CAPEX sign convention is unresolved")
    else:
        fcf_value = ocf - capex
        fcf = MetricValue("FIN.FCF", fcf_value, "currency", MetricStatus.CALCULATED)
        fcf_margin = _ratio("FIN.FCF_MARGIN", fcf_value, revenue)
    results.extend([fcf, fcf_margin])
    return results


def calculate_growth(current: Decimal | None, previous: Decimal | None) -> MetricValue:
    if current is None or previous is None:
        return MetricValue("FIN.REVENUE_GROWTH", None, "ratio", MetricStatus.UNAVAILABLE,
                           "Current and previous revenue required")
    if previous <= ZERO:
        return MetricValue("FIN.REVENUE_GROWTH", None, "ratio", MetricStatus.INVALID_INPUT,
                           "Previous revenue must be positive")
    return MetricValue("FIN.REVENUE_GROWTH", current / previous - ONE, "ratio", MetricStatus.CALCULATED)


def calculate_cagr(start_value: Decimal | None, end_value: Decimal | None,
                   years: int) -> MetricValue:
    if start_value is None or end_value is None:
        return MetricValue("FIN.REVENUE_CAGR", None, "ratio", MetricStatus.UNAVAILABLE,
                           "Start and end revenue required")
    if start_value <= ZERO or end_value <= ZERO or years <= 0:
        return MetricValue("FIN.REVENUE_CAGR", None, "ratio", MetricStatus.INVALID_INPUT,
                           "Positive endpoints and a positive year interval are required")
    with localcontext() as ctx:
        ctx.prec = 28
        # Decimal fractional powers are supported by Python's Decimal implementation.
        value = (end_value / start_value) ** (ONE / Decimal(years)) - ONE
    return MetricValue("FIN.REVENUE_CAGR", value, "ratio", MetricStatus.CALCULATED)


def to_decimal(value: object) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Invalid decimal input") from exc
    if not result.is_finite():
        raise ValueError("Financial values must be finite")
    return result
