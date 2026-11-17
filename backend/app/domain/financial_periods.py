from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class PeriodKind(StrEnum):
    INSTANT = "INSTANT"
    QUARTER = "QUARTER"
    YTD = "YTD"
    ANNUAL = "ANNUAL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class PeriodDescriptor:
    kind: PeriodKind
    duration_days: int | None


def classify_sec_period(
    *, start: date | None, end: date, form: str | None, fiscal_period: str | None
) -> PeriodDescriptor:
    """Conservative SEC duration classifier; never infers a fiscal calendar from end date."""
    if start is None:
        return PeriodDescriptor(PeriodKind.INSTANT, None)
    duration = (end - start).days + 1
    form = (form or "").upper()
    fp = (fiscal_period or "").upper()
    if form == "10-K" and duration >= 330:
        return PeriodDescriptor(PeriodKind.ANNUAL, duration)
    if form == "10-Q":
        if fp == "Q1" and 60 <= duration <= 120:
            return PeriodDescriptor(PeriodKind.QUARTER, duration)
        if fp in {"Q2", "Q3"}:
            if 60 <= duration <= 120:
                return PeriodDescriptor(PeriodKind.QUARTER, duration)
            if 150 <= duration <= 300:
                return PeriodDescriptor(PeriodKind.YTD, duration)
    if duration >= 330 and form in {"20-F", "40-F"}:
        return PeriodDescriptor(PeriodKind.ANNUAL, duration)
    return PeriodDescriptor(PeriodKind.UNKNOWN, duration)
