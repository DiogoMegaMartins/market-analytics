from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class FindingSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    REVIEW = "REVIEW"
    BLOCKER = "BLOCKER"


@dataclass(frozen=True)
class QualityFinding:
    rule_id: str
    severity: FindingSeverity
    message: str
    metric_id: str | None = None


def validate_fact_set(facts: list[object]) -> list[QualityFinding]:
    """Checks a coherent annual input set without silently changing reported values."""
    findings: list[QualityFinding] = []
    by_metric: dict[str, list[object]] = {}
    for fact in facts:
        by_metric.setdefault(str(fact.metric_id), []).append(fact)
    for metric_id, rows in by_metric.items():
        if len(rows) > 1:
            findings.append(QualityFinding("DUPLICATE_PERIOD", FindingSeverity.REVIEW,
                                           "More than one candidate exists for the same metric period.", metric_id))
    relevant = [f for f in facts if getattr(f, "metric_id", None) in {
        "FIN.REVENUE", "FIN.GROSS_PROFIT", "FIN.OPERATING_INCOME", "FIN.NET_INCOME", "FIN.OCF", "FIN.CAPEX"
    }]
    currencies = {getattr(f, "currency", None) for f in relevant if getattr(f, "currency", None)}
    units = {getattr(f, "unit", None) for f in relevant}
    if len(currencies) > 1:
        findings.append(QualityFinding("CURRENCY_MISMATCH", FindingSeverity.BLOCKER,
                                       "Inputs use different currencies; cross-currency calculations are blocked."))
    if len(units) > 1:
        findings.append(QualityFinding("UNIT_MISMATCH", FindingSeverity.BLOCKER,
                                       "Inputs use different units; calculations are blocked."))
    years = {getattr(f, "fiscal_year", None) for f in relevant}
    if len(years) > 1:
        findings.append(QualityFinding("PERIOD_MISMATCH", FindingSeverity.BLOCKER,
                                       "Inputs do not belong to the same fiscal year."))
    for fact in relevant:
        if getattr(fact, "metric_id", None) == "FIN.CAPEX" and getattr(fact, "value", Decimal(0)) < 0:
            findings.append(QualityFinding("UNEXPECTED_CAPEX_SIGN", FindingSeverity.REVIEW,
                                           "CAPEX is negative; confirm provider sign convention before FCF.",
                                           "FIN.CAPEX"))
    return findings
