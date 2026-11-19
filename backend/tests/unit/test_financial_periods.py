from datetime import date

from app.domain.financial_periods import PeriodKind, classify_sec_period


def test_classifies_instant_fact() -> None:
    result = classify_sec_period(start=None, end=date(2025, 12, 31), form="10-K", fiscal_period="FY")
    assert result.kind == PeriodKind.INSTANT
    assert result.duration_days is None


def test_classifies_annual_duration() -> None:
    result = classify_sec_period(start=date(2025, 1, 1), end=date(2025, 12, 31), form="10-K", fiscal_period="FY")
    assert result.kind == PeriodKind.ANNUAL


def test_classifies_quarter_and_ytd_separately() -> None:
    quarter = classify_sec_period(start=date(2025, 4, 1), end=date(2025, 6, 30), form="10-Q", fiscal_period="Q2")
    ytd = classify_sec_period(start=date(2025, 1, 1), end=date(2025, 6, 30), form="10-Q", fiscal_period="Q2")
    assert quarter.kind == PeriodKind.QUARTER
    assert ytd.kind == PeriodKind.YTD


def test_does_not_guess_unknown_duration() -> None:
    result = classify_sec_period(start=date(2025, 2, 1), end=date(2025, 4, 1), form="8-K", fiscal_period="Q1")
    assert result.kind == PeriodKind.UNKNOWN
