from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from itertools import pairwise
from typing import Protocol


class HistoricalFact(Protocol):
    metric_id: str
    value: Decimal
    unit: str
    currency: str | None
    period_kind: str
    fiscal_period: str | None
    fiscal_year: int | None
    start_date: date | None
    end_date: date
    filed_at: date | None


@dataclass(frozen=True)
class RestatementChange:
    metric_id: str
    fiscal_year: int | None
    fiscal_period: str | None
    old_value: Decimal
    new_value: Decimal
    absolute_change: Decimal
    relative_change: Decimal | None
    old_filed_at: date | None
    new_filed_at: date | None
    material: bool


def detect_restatements(
    facts: Iterable[HistoricalFact], *, materiality_threshold: Decimal = Decimal("0.05")
) -> list[RestatementChange]:
    """Compare successive filings for the same economic period; threshold is a review heuristic."""
    if materiality_threshold < 0:
        raise ValueError("materiality_threshold cannot be negative")
    groups: dict[tuple, list[HistoricalFact]] = {}
    for fact in facts:
        key = (fact.metric_id, fact.unit, fact.currency, fact.period_kind,
               fact.fiscal_year, fact.fiscal_period, fact.start_date, fact.end_date)
        groups.setdefault(key, []).append(fact)

    changes: list[RestatementChange] = []
    for key, candidates in groups.items():
        candidates.sort(key=lambda item: (item.filed_at or date.min))
        for old, new in pairwise(candidates):
            if old.value == new.value:
                continue
            absolute = new.value - old.value
            relative = abs(absolute) / abs(old.value) if old.value != 0 else None
            material = relative is None or relative >= materiality_threshold
            changes.append(RestatementChange(
                metric_id=key[0], fiscal_year=key[4], fiscal_period=key[5],
                old_value=old.value, new_value=new.value, absolute_change=absolute,
                relative_change=relative, old_filed_at=old.filed_at,
                new_filed_at=new.filed_at, material=material,
            ))
    return changes


@dataclass(frozen=True)
class QuarterlyObservation:
    metric_id: str
    value: Decimal
    unit: str
    currency: str | None
    start_date: date
    end_date: date
    fiscal_year: int | None = None
    fiscal_period: str | None = None


@dataclass(frozen=True)
class TTMResult:
    metric_id: str
    value: Decimal
    unit: str
    currency: str | None
    period_start: date
    period_end: date
    quarter_count: int = 4


def calculate_ttm(observations: Iterable[QuarterlyObservation]) -> TTMResult:
    """Sum four consecutive standalone quarterly flow observations, without calendar-year assumptions."""
    rows = sorted(observations, key=lambda item: item.end_date)
    if len(rows) != 4:
        raise ValueError("TTM requires exactly four quarterly observations")
    first = rows[0]
    for row in rows:
        if row.metric_id != first.metric_id or row.unit != first.unit or row.currency != first.currency:
            raise ValueError("TTM observations must share metric, unit and currency")
        if row.start_date > row.end_date:
            raise ValueError("Quarter start date must not follow end date")
    if len({row.end_date for row in rows}) != 4:
        raise ValueError("TTM observations must have unique quarter end dates")
    for previous, current in pairwise(rows):
        gap = (current.end_date - previous.end_date).days
        if not 70 <= gap <= 110:
            raise ValueError("TTM observations must be consecutive quarterly periods")
    for row in rows:
        duration = (row.end_date - row.start_date).days + 1
        if not 60 <= duration <= 120:
            raise ValueError("TTM requires standalone quarterly, not YTD or annual, observations")
    return TTMResult(
        metric_id=first.metric_id, value=sum((row.value for row in rows), Decimal(0)),
        unit=first.unit, currency=first.currency, period_start=rows[0].start_date,
        period_end=rows[-1].end_date,
    )
