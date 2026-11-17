from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.financial_data.quarter_derivation import derive_quarter


def _fact(value, *, period, end, unit="USD", currency="USD", year=2024, company_id=None):
    return SimpleNamespace(
        id=uuid4(), company_id=company_id or uuid4(), metric_id="FIN.REVENUE", fiscal_year=year,
        unit=unit, currency=currency, value=Decimal(value), end_date=end,
        start_date=date(year, 1, 1), period_kind=period, fiscal_period="Q1",
        source_fact_id=uuid4(), filed_at=date(year, 8, 1),
        available_at=datetime.now(UTC),
    )


def test_q2_is_ytd_minus_q1():
    company_id = uuid4()
    q1 = _fact("100", period="QUARTER", end=date(2024, 3, 31), company_id=company_id)
    q2_ytd = _fact("230", period="YTD", end=date(2024, 6, 30), company_id=company_id)
    result = derive_quarter(metric_id="FIN.REVENUE", fiscal_year=2024,
                            fiscal_period="Q2", minuend=q2_ytd, subtrahend=q1)
    assert result.value == Decimal(130)
    assert result.start_date == date(2024, 4, 1)


def test_quarter_derivation_rejects_currency_mismatch():
    company_id = uuid4()
    ytd = _fact("230", period="YTD", end=date(2024, 6, 30), currency="USD", company_id=company_id)
    q1 = _fact("100", period="QUARTER", end=date(2024, 3, 31), currency="EUR", company_id=company_id)
    with pytest.raises(ValueError, match="currency"):
        derive_quarter(metric_id="FIN.REVENUE", fiscal_year=2024,
                       fiscal_period="Q2", minuend=ytd, subtrahend=q1)
