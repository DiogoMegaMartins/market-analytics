from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.financial_periods import classify_sec_period
from app.models.financial_data import (
    FinancialFact,
    FinancialFactLineage,
    NormalizedFinancialFact,
    SECProviderCache,
    SECRawCompanyFacts,
)
from app.providers.sec.client import SECClient

# Ordered alternatives: choose the first populated tag, never add alternatives together.
SEC_TAG_MAP: dict[str, tuple[str, ...]] = {
    "FIN.REVENUE": (
        "RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet",
    ),
    "FIN.GROSS_PROFIT": ("GrossProfit",),
    "FIN.OPERATING_INCOME": ("OperatingIncomeLoss",),
    "FIN.NET_INCOME": ("NetIncomeLoss", "ProfitLoss"),
    "FIN.OCF": ("NetCashProvidedByUsedInOperatingActivities",),
    "FIN.CAPEX": ("PaymentsToAcquirePropertyPlantAndEquipment",),
}


def _as_date(value: str | None):
    from datetime import date
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _currency_for_unit(unit: str) -> str | None:
    return unit if len(unit) == 3 and unit.isalpha() else None


def _external_key(parts: tuple[Any, ...]) -> str:
    return sha256("|".join("" if part is None else str(part) for part in parts).encode()).hexdigest()


class SECCompanyFactsImportService:
    def __init__(self, client: SECClient | None = None) -> None:
        self.client = client or SECClient()

    async def _get_payload(
        self, session: AsyncSession, *, cik: str, source_url: str,
    ) -> tuple[dict[str, Any], str, str, datetime, bool]:
        now = datetime.now(UTC)
        cache_key = f"companyfacts:{cik}"
        cached = await session.scalar(select(SECProviderCache).where(
            SECProviderCache.provider == "SEC",
            SECProviderCache.cache_key == cache_key,
            SECProviderCache.expires_at > now,
        ))
        if cached is not None:
            payload = json.loads(cached.payload_text, parse_float=Decimal, parse_int=int)
            return payload, cached.payload_text, cached.payload_hash, cached.fetched_at, True

        # Release the read transaction before network I/O; provider latency must not
        # hold database connections/locks while waiting for SEC.
        await session.commit()
        payload, raw_text, payload_hash = await self.client.company_facts(cik)
        fetched_at = datetime.now(UTC)
        ttl = get_settings().sec_company_facts_cache_ttl_seconds
        expires_at = fetched_at + timedelta(seconds=ttl)
        statement = pg_insert(SECProviderCache).values(
            provider="SEC", cache_key=cache_key, source_url=source_url,
            payload_hash=payload_hash, payload_text=raw_text,
            fetched_at=fetched_at, expires_at=expires_at,
        ).on_conflict_do_update(
            index_elements=["provider", "cache_key"],
            set_={
                "source_url": source_url, "payload_hash": payload_hash,
                "payload_text": raw_text, "fetched_at": fetched_at,
                "expires_at": expires_at,
            },
        )
        await session.execute(statement)
        return payload, raw_text, payload_hash, fetched_at, False

    async def import_company(
        self, session: AsyncSession, *, company_id: UUID, cik: str,
    ) -> dict[str, Any]:
        padded_cik = SECClient.normalize_cik(cik)
        source_url = self.client.COMPANY_FACTS_URL.format(cik=padded_cik)
        payload, raw_text, payload_hash, retrieved_at, cache_hit = await self._get_payload(
            session, cik=padded_cik, source_url=source_url,
        )
        facts_root = payload.get("facts", {})
        us_gaap = facts_root.get("us-gaap", {}) if isinstance(facts_root, dict) else {}
        if not isinstance(us_gaap, dict):
            await session.rollback()
            raise TypeError("SEC Company Facts response has no valid us-gaap taxonomy")

        # Database uniqueness is the concurrency authority; no select-then-insert race.
        raw_statement = pg_insert(SECRawCompanyFacts).values(
            company_id=company_id, cik=padded_cik, provider="SEC", source_url=source_url,
            payload_hash=payload_hash, payload_text=raw_text, retrieved_at=retrieved_at,
            connector_version="sec-companyfacts-v1",
        ).on_conflict_do_nothing(
            index_elements=["cik", "payload_hash"]
        ).returning(SECRawCompanyFacts.id)
        raw_record_id = (await session.execute(raw_statement)).scalar_one_or_none()
        if raw_record_id is None:
            raw_record_id = await session.scalar(select(SECRawCompanyFacts.id).where(
                SECRawCompanyFacts.cik == padded_cik,
                SECRawCompanyFacts.payload_hash == payload_hash,
            ))
        if raw_record_id is None:
            await session.rollback()
            raise RuntimeError("Could not persist SEC raw payload")

        imported = 0
        skipped = 0
        normalized_created = 0
        for metric_id, tags in SEC_TAG_MAP.items():
            selected_tag = next((
                tag for tag in tags
                if tag in us_gaap and isinstance(us_gaap[tag], dict)
                and us_gaap[tag].get("units")
            ), None)
            if selected_tag is None:
                continue
            units = us_gaap[selected_tag].get("units", {})
            for unit, observations in units.items():
                for observation in observations:
                    value = observation.get("val")
                    if value is None:
                        skipped += 1
                        continue
                    try:
                        decimal_value = Decimal(str(value))
                    except (InvalidOperation, ValueError, TypeError):
                        skipped += 1
                        continue
                    if not decimal_value.is_finite():
                        skipped += 1
                        continue
                    end_date = _as_date(observation.get("end"))
                    if end_date is None:
                        skipped += 1
                        continue
                    start_date = _as_date(observation.get("start"))
                    filed_at = _as_date(observation.get("filed"))
                    form = observation.get("form")
                    fiscal_period = observation.get("fp")
                    period = classify_sec_period(
                        start=start_date, end=end_date, form=form, fiscal_period=fiscal_period,
                    )
                    accession = observation.get("accn")
                    fiscal_year = observation.get("fy")
                    external_key = _external_key((
                        padded_cik, metric_id, selected_tag, unit, decimal_value,
                        start_date, end_date, fiscal_year, fiscal_period, form,
                        accession, filed_at, observation.get("frame"),
                    ))
                    fact_statement = pg_insert(FinancialFact).values(
                        company_id=company_id, raw_record_id=raw_record_id, cik=padded_cik,
                        external_fact_key=external_key, metric_id=metric_id,
                        taxonomy="us-gaap", tag=selected_tag, value=decimal_value,
                        unit=unit, currency=_currency_for_unit(unit),
                        period_kind=period.kind.value, start_date=start_date, end_date=end_date,
                        fiscal_year=int(fiscal_year) if fiscal_year is not None else None,
                        fiscal_period=fiscal_period, form=form, accession_number=accession,
                        filed_at=filed_at, frame=observation.get("frame"),
                        retrieved_at=retrieved_at, mapping_version="sec-us-gaap-v1",
                    ).on_conflict_do_nothing(
                        index_elements=["external_fact_key"]
                    ).returning(FinancialFact.id)
                    fact_id = (await session.execute(fact_statement)).scalar_one_or_none()
                    if fact_id is None:
                        skipped += 1
                        continue

                    normalized_key = _external_key((
                        "reported", fact_id, metric_id, period.kind.value, "sec-us-gaap-v1",
                    ))
                    normalized_statement = pg_insert(NormalizedFinancialFact).values(
                        company_id=company_id, source_fact_id=fact_id, metric_id=metric_id,
                        value=decimal_value, unit=unit, currency=_currency_for_unit(unit),
                        period_kind=period.kind.value,
                        fiscal_year=int(fiscal_year) if fiscal_year is not None else None,
                        fiscal_period=fiscal_period, start_date=start_date, end_date=end_date,
                        origin="REPORTED", normalized_key=normalized_key,
                        filed_at=filed_at, available_at=retrieved_at,
                        derivation_version="sec-us-gaap-v1",
                    ).on_conflict_do_nothing(
                        index_elements=["normalized_key"]
                    ).returning(NormalizedFinancialFact.id)
                    normalized_id = (await session.execute(normalized_statement)).scalar_one_or_none()
                    if normalized_id is not None:
                        lineage_statement = pg_insert(FinancialFactLineage).values(
                            normalized_fact_id=normalized_id, source_fact_id=fact_id,
                            role="DIRECT_SOURCE",
                        ).on_conflict_do_nothing(
                            index_elements=["normalized_fact_id", "source_fact_id", "role"]
                        )
                        await session.execute(lineage_statement)
                        normalized_created += 1
                    imported += 1

        await session.commit()
        return {
            "company_id": str(company_id), "cik": padded_cik,
            "raw_record_id": str(raw_record_id), "payload_hash": payload_hash,
            "imported_facts": imported, "normalized_facts": normalized_created,
            "skipped_observations": skipped, "retrieved_at": retrieved_at.isoformat(),
            "cache_hit": cache_hit, "mapping_version": "sec-us-gaap-v1",
        }
