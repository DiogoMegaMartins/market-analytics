import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.services.metrics.calculator import calculate_annual_metrics
from app.services.metrics.reference_validation import (
    FinancialObservation,
    ReconciliationStatus,
    ReferenceObservation,
    reconcile_observations,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "reference_financials_2024.json"


def load_reference():
    return json.loads(FIXTURE.read_text())


@pytest.mark.parametrize("ticker", ["MSFT", "AAPL", "KO"])
def test_fy2024_reference_income_statement_and_margins(ticker):
    company = next(item for item in load_reference()["companies"] if item["ticker"] == ticker)
    facts = {key: Decimal(value) for key, value in company["facts"].items()}
    calculated = {item.metric_id: item for item in calculate_annual_metrics(facts)}

    revenue = facts["FIN.REVENUE"]
    assert calculated["FIN.GROSS_MARGIN"].value == facts["FIN.GROSS_PROFIT"] / revenue
    assert calculated["FIN.OPERATING_MARGIN"].value == facts["FIN.OPERATING_INCOME"] / revenue
    assert calculated["FIN.NET_MARGIN"].value == facts["FIN.NET_INCOME"] / revenue


def test_reference_reconciliation_matches_and_preserves_source():
    company = next(item for item in load_reference()["companies"] if item["ticker"] == "MSFT")
    actual = {}
    references = {}
    for metric_id, raw_value in company["facts"].items():
        value = Decimal(raw_value)
        actual[metric_id] = FinancialObservation(
            metric_id, value, "USD", "USD", company["period_end"]
        )
        references[metric_id] = ReferenceObservation(
            metric_id, value, "USD", "USD", company["period_end"],
            company["source_name"], company["source_url"],
        )
    results = reconcile_observations(actual, references)
    assert all(result.status == ReconciliationStatus.MATCH for result in results)
    assert all(result.source_url == company["source_url"] for result in results)


def test_reference_reconciliation_detects_mismatch_missing_and_period():
    reference = ReferenceObservation(
        "FIN.REVENUE", Decimal(100), "USD", "USD", "2024-12-31",
        "Annual report", "https://example.test/annual-report",
    )
    results = reconcile_observations(
        {
            "FIN.REVENUE": FinancialObservation(
                "FIN.REVENUE", Decimal(120), "USD", "USD", "2024-12-31"
            ),
            "FIN.OPERATING_INCOME": FinancialObservation(
                "FIN.OPERATING_INCOME", Decimal(10), "USD", "USD", "2023-12-31"
            ),
        },
        {
            "FIN.REVENUE": reference,
            "FIN.OPERATING_INCOME": ReferenceObservation(
                "FIN.OPERATING_INCOME", Decimal(10), "USD", "USD", "2024-12-31",
                "Annual report", "https://example.test/annual-report",
            ),
            "FIN.NET_INCOME": ReferenceObservation(
                "FIN.NET_INCOME", Decimal(5), "USD", "USD", "2024-12-31",
                "Annual report", "https://example.test/annual-report",
            ),
        },
    )
    assert [item.status for item in results] == [
        ReconciliationStatus.MISMATCH,
        ReconciliationStatus.INCOMPATIBLE_PERIOD,
        ReconciliationStatus.MISSING,
    ]


def test_reference_reconciliation_rejects_unit_mismatch():
    reference = ReferenceObservation(
        "FIN.REVENUE", Decimal(100), "USD", "USD", "2024-12-31",
        "Annual report", "https://example.test/annual-report",
    )
    actual = {
        "FIN.REVENUE": FinancialObservation(
            "FIN.REVENUE", Decimal(100), "shares", None, "2024-12-31"
        )
    }
    result = reconcile_observations(actual, {"FIN.REVENUE": reference})[0]
    assert result.status == ReconciliationStatus.INCOMPATIBLE_UNIT
