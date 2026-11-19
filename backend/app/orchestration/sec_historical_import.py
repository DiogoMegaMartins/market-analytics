"""Controlled, sequential SEC Company Facts imports for the initial research universe."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.financial_data.sec_company_facts import SECCompanyFactsImportService

# SEC CIKs are stable issuer identifiers; company UUIDs must come from the existing database.
SEC_HISTORICAL_UNIVERSE: dict[str, str] = {
    "MSFT": "0000789019",
    "KO": "0000021344",
    "COST": "0000909832",
    "CAT": "0000018230",
    "XOM": "0000034088",
}


@dataclass(frozen=True)
class SECHistoricalImportTarget:
    ticker: str
    cik: str
    company_id: UUID


@dataclass(frozen=True)
class SECHistoricalImportResult:
    ticker: str
    cik: str
    status: str
    details: dict[str, Any] | None = None
    error_type: str | None = None


def build_default_sec_targets(
    company_ids: Mapping[str, UUID],
) -> tuple[SECHistoricalImportTarget, ...]:
    """Build targets for known tickers; never creates or guesses company records."""
    unknown = set(company_ids) - set(SEC_HISTORICAL_UNIVERSE)
    if unknown:
        raise ValueError(f"Unsupported SEC universe ticker(s): {', '.join(sorted(unknown))}")

    return tuple(
        SECHistoricalImportTarget(ticker=ticker, cik=SEC_HISTORICAL_UNIVERSE[ticker], company_id=company_ids[ticker])
        for ticker in SEC_HISTORICAL_UNIVERSE
        if ticker in company_ids
    )


class SECHistoricalImportOrchestrator:
    """Run one issuer at a time so failures are isolated and results auditable."""

    def __init__(self, importer: SECCompanyFactsImportService | None = None) -> None:
        self.importer = importer or SECCompanyFactsImportService()

    async def import_targets(
        self,
        session: AsyncSession,
        targets: Sequence[SECHistoricalImportTarget],
    ) -> list[SECHistoricalImportResult]:
        tickers = [target.ticker for target in targets]
        if len(tickers) != len(set(tickers)):
            raise ValueError("SEC import targets must not contain duplicate tickers")
        company_ids = [target.company_id for target in targets]
        if len(company_ids) != len(set(company_ids)):
            raise ValueError("SEC import targets must not reuse a company_id")
        for target in targets:
            expected_cik = SEC_HISTORICAL_UNIVERSE.get(target.ticker)
            if expected_cik is None or target.cik != expected_cik:
                raise ValueError(f"Ticker/CIK pair is not in the approved SEC universe: {target.ticker}")

        results: list[SECHistoricalImportResult] = []
        for target in targets:
            try:
                details = await self.importer.import_company(
                    session, company_id=target.company_id, cik=target.cik,
                )
            except Exception as exc:  # noqa: BLE001 — isolate issuer failures; cancellation is not swallowed
                await session.rollback()
                results.append(SECHistoricalImportResult(
                    ticker=target.ticker,
                    cik=target.cik,
                    status="FAILED",
                    error_type=type(exc).__name__,
                ))
            else:
                results.append(SECHistoricalImportResult(
                    ticker=target.ticker,
                    cik=target.cik,
                    status="IMPORTED",
                    details=details,
                ))
        return results
