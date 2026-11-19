from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum


class ReconciliationStatus(StrEnum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    MISSING = "MISSING"
    INCOMPATIBLE_UNIT = "INCOMPATIBLE_UNIT"
    INCOMPATIBLE_PERIOD = "INCOMPATIBLE_PERIOD"
    AMBIGUOUS_SOURCE = "AMBIGUOUS_SOURCE"


@dataclass(frozen=True)
class FinancialObservation:
    metric_id: str
    value: Decimal
    unit: str
    currency: str | None
    period_end: str


@dataclass(frozen=True)
class ReferenceObservation:
    metric_id: str
    value: Decimal
    unit: str
    currency: str | None
    period_end: str
    source_name: str
    source_url: str
    period_kind: str | None = None


@dataclass(frozen=True)
class ReconciliationResult:
    metric_id: str
    status: ReconciliationStatus
    actual_value: Decimal | None
    reference_value: Decimal
    absolute_difference: Decimal | None
    allowed_difference: Decimal
    source_name: str
    source_url: str


def reconcile_observations(
    actual: Mapping[str, FinancialObservation],
    references: Mapping[str, ReferenceObservation],
    *,
    absolute_tolerance: Decimal = Decimal(1),
    relative_tolerance: Decimal = Decimal("0.000001"),
) -> list[ReconciliationResult]:
    """Compare normalized facts with curated filing references; never changes actual data."""
    if absolute_tolerance < 0 or relative_tolerance < 0:
        raise ValueError("Tolerances cannot be negative")
    results: list[ReconciliationResult] = []
    for metric_id, reference in references.items():
        observed = actual.get(metric_id)
        allowed = max(absolute_tolerance, abs(reference.value) * relative_tolerance)
        if observed is None:
            status, actual_value, difference = ReconciliationStatus.MISSING, None, None
        elif observed.unit != reference.unit or observed.currency != reference.currency:
            status, actual_value, difference = ReconciliationStatus.INCOMPATIBLE_UNIT, observed.value, None
        elif observed.period_end != reference.period_end:
            status, actual_value, difference = ReconciliationStatus.INCOMPATIBLE_PERIOD, observed.value, None
        else:
            actual_value = observed.value
            difference = abs(observed.value - reference.value)
            status = ReconciliationStatus.MATCH if difference <= allowed else ReconciliationStatus.MISMATCH
        results.append(ReconciliationResult(
            metric_id=metric_id, status=status, actual_value=actual_value,
            reference_value=reference.value, absolute_difference=difference,
            allowed_difference=allowed, source_name=reference.source_name,
            source_url=reference.source_url,
        ))
    return results


def reconcile_fact_rows(
    rows,
    references: Mapping[str, ReferenceObservation],
    *,
    absolute_tolerance: Decimal = Decimal(1),
    relative_tolerance: Decimal = Decimal("0.000001"),
) -> list[ReconciliationResult]:
    """Reconcile persisted normalized-fact-like rows without guessing between contexts.

    Rows must expose metric_id, value, unit, currency, end_date and optionally filed_at.
    Only rows matching the reference period are considered. Multiple different values
    for the same metric/period are reported as AMBIGUOUS_SOURCE rather than silently
    choosing a filing or XBRL context.
    """
    grouped = {}
    for row in rows:
        grouped.setdefault(row.metric_id, []).append(row)

    results: list[ReconciliationResult] = []
    for metric_id, reference in references.items():
        candidates = [
            row for row in grouped.get(metric_id, [])
            if row.end_date.isoformat() == reference.period_end
            and (reference.period_kind is None or row.period_kind == reference.period_kind)
        ]
        allowed = max(absolute_tolerance, abs(reference.value) * relative_tolerance)
        if not candidates:
            results.append(ReconciliationResult(
                metric_id, ReconciliationStatus.MISSING, None, reference.value, None,
                allowed, reference.source_name, reference.source_url,
            ))
            continue

        unit_pairs = {(row.unit, row.currency) for row in candidates}
        if len(unit_pairs) != 1:
            results.append(ReconciliationResult(
                metric_id, ReconciliationStatus.INCOMPATIBLE_UNIT, None, reference.value,
                None, allowed, reference.source_name, reference.source_url,
            ))
            continue

        values = {Decimal(str(row.value)) for row in candidates}
        if len(values) > 1:
            results.append(ReconciliationResult(
                metric_id, ReconciliationStatus.AMBIGUOUS_SOURCE, None, reference.value,
                None, allowed, reference.source_name, reference.source_url,
            ))
            continue

        row = max(candidates, key=lambda item: (
            item.filed_at or date.min,
            getattr(item, "available_at", None) or datetime.min.replace(tzinfo=UTC),
        ))
        observed = FinancialObservation(
            metric_id=metric_id, value=Decimal(str(row.value)), unit=row.unit,
            currency=row.currency, period_end=row.end_date.isoformat(),
        )
        result = reconcile_observations(
            {metric_id: observed}, {metric_id: reference},
            absolute_tolerance=absolute_tolerance,
            relative_tolerance=relative_tolerance,
        )[0]
        results.append(result)
    return results
