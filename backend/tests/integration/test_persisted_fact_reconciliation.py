from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.services.metrics.reference_validation import (
    ReconciliationStatus,
    ReferenceObservation,
    reconcile_fact_rows,
)


def ref():
    return ReferenceObservation(
        "FIN.REVENUE", Decimal(100), "USD", "USD", "2024-12-31",
        "Annual report", "https://example.test/report", "ANNUAL",
    )


def row(value="100", unit="USD", currency="USD", end_date=date(2024, 12, 31), filed_at=None):
    return SimpleNamespace(
        metric_id="FIN.REVENUE", value=Decimal(value), unit=unit,
        currency=currency, end_date=end_date, filed_at=filed_at,
        available_at=datetime(2025, 2, 1, tzinfo=UTC),
        period_kind="ANNUAL",
    )


def test_persisted_fact_rows_match_reference():
    result = reconcile_fact_rows([row()], {"FIN.REVENUE": ref()})[0]
    assert result.status == ReconciliationStatus.MATCH


def test_persisted_fact_rows_detect_ambiguous_contexts():
    result = reconcile_fact_rows(
        [row("100"), row("95")], {"FIN.REVENUE": ref()}
    )[0]
    assert result.status == ReconciliationStatus.AMBIGUOUS_SOURCE


def test_persisted_fact_rows_do_not_match_other_periods():
    result = reconcile_fact_rows(
        [row(end_date=date(2023, 12, 31))], {"FIN.REVENUE": ref()}
    )[0]
    assert result.status == ReconciliationStatus.MISSING


def test_persisted_fact_rows_detect_incompatible_units():
    result = reconcile_fact_rows(
        [row(unit="shares", currency=None)], {"FIN.REVENUE": ref()}
    )[0]
    assert result.status == ReconciliationStatus.INCOMPATIBLE_UNIT


def test_persisted_fact_rows_ignore_quarter_with_same_period_end():
    quarterly = row("95")
    quarterly.period_kind = "QUARTER"
    annual = row("100")
    result = reconcile_fact_rows(
        [quarterly, annual], {"FIN.REVENUE": ref()}
    )[0]
    assert result.status == ReconciliationStatus.MATCH
