from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.services.metrics.quality import FindingSeverity, validate_fact_set


def _fact(metric_id, value=Decimal(1), unit="USD", currency="USD", year=2024):
    return SimpleNamespace(metric_id=metric_id, value=value, unit=unit, currency=currency,
                           fiscal_year=year, end_date=date(2024, 12, 31),
                           available_at=datetime.now(UTC))


def test_currency_and_unit_mismatch_block_cross_input_calculations():
    findings = validate_fact_set([
        _fact("FIN.REVENUE", unit="USD", currency="USD"),
        _fact("FIN.OCF", unit="EUR", currency="EUR"),
    ])
    assert {f.rule_id for f in findings} >= {"CURRENCY_MISMATCH", "UNIT_MISMATCH"}
    assert any(f.severity == FindingSeverity.BLOCKER for f in findings)


def test_negative_capex_requires_review():
    findings = validate_fact_set([_fact("FIN.CAPEX", value=Decimal(-5))])
    assert any(f.rule_id == "UNEXPECTED_CAPEX_SIGN" for f in findings)
