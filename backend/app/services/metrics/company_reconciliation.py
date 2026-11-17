from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_data import NormalizedFinancialFact
from app.models.identity import AssetIdentifier, IdentifierType
from app.services.metrics.reference_validation import ReferenceObservation, reconcile_fact_rows

REFERENCE_FILE = Path(__file__).parents[2] / "data" / "reference_financials_2024.json"


def load_reference_company(ticker: str) -> dict[str, Any]:
    catalog = json.loads(REFERENCE_FILE.read_text(encoding="utf-8"))
    normalized_ticker = ticker.strip().upper()
    for company in catalog["companies"]:
        if company["ticker"].upper() == normalized_ticker:
            return company
    raise KeyError(f"No reference dataset for ticker {normalized_ticker}")


async def reconcile_company_against_reference(
    session: AsyncSession, *, company_id: UUID, ticker: str,
):
    company = load_reference_company(ticker)
    identifier = await session.scalar(select(AssetIdentifier).where(
        AssetIdentifier.company_id == company_id,
        AssetIdentifier.identifier_type == IdentifierType.TICKER.value,
        AssetIdentifier.value == ticker.upper(),
    ))
    if identifier is None:
        raise LookupError("Ticker is not registered for this company")
    rows = list((await session.scalars(select(NormalizedFinancialFact).where(
        NormalizedFinancialFact.company_id == company_id,
        NormalizedFinancialFact.fiscal_year == company["fiscal_year"],
    ))).all())
    references = {
        metric_id: ReferenceObservation(
            metric_id=metric_id,
            value=Decimal(raw_value),
            unit=company["amount_unit"],
            currency=company["amount_unit"],
            period_end=company["period_end"],
            source_name=company["source_name"],
            source_url=company["source_url"],
            period_kind=company.get("period_kind"),
        )
        for metric_id, raw_value in company["facts"].items()
    }
    results = reconcile_fact_rows(rows, references)
    return company, results
