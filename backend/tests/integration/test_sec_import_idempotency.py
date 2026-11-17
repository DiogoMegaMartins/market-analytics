"""Exercise the real SEC import service against disposable PostgreSQL."""
import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.services.financial_data.sec_company_facts import SECCompanyFactsImportService

DATABASE_URL = __import__("os").environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL is not configured")


class FixtureSECClient:
    COMPANY_FACTS_URL = "https://example.test/submissions/CIK{cik}.json"

    async def company_facts(self, cik: str):
        payload = {"facts": {"us-gaap": {"RevenueFromContractWithCustomerExcludingAssessedTax": {
            "units": {"USD": [
                {"val": 100, "start": "2024-01-01", "end": "2024-12-31", "filed": "2025-02-01", "fy": 2024, "fp": "FY", "form": "10-K", "accn": "0000000001-25-000001"},
                {"val": 110, "start": "2024-01-01", "end": "2024-12-31", "filed": "2025-03-01", "fy": 2024, "fp": "FY", "form": "10-K/A", "accn": "0000000001-25-000002"},
            ]}
        }}}}
        raw = '{"fixture":"sec-import"}'
        return payload, raw, "b" * 64


@pytest.mark.asyncio
async def test_real_import_twice_is_idempotent_and_preserves_restatement() -> None:
    engine = create_async_engine(DATABASE_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    company_id = uuid4()
    try:
        async with engine.begin() as connection:
            await connection.execute(text(
                "INSERT INTO companies (id, legal_name, status, created_at, updated_at) "
                "VALUES (:id, 'SEC fixture company', 'ACTIVE', now(), now())"
            ), {"id": company_id})
        service = SECCompanyFactsImportService(FixtureSECClient())
        async with factory() as session:
            first = await service.import_company(session, company_id=company_id, cik="1")
            second = await service.import_company(session, company_id=company_id, cik="1")
            assert first["imported_facts"] == 2
            assert second["imported_facts"] == 0
            assert second["cache_hit"] is True
        async with engine.connect() as connection:
            counts = await connection.execute(text(
                "SELECT (SELECT count(*) FROM sec_raw_company_facts WHERE company_id = :id), "
                "(SELECT count(*) FROM financial_facts WHERE company_id = :id), "
                "(SELECT count(*) FROM normalized_financial_facts WHERE company_id = :id), "
                "(SELECT count(*) FROM financial_fact_lineage l JOIN normalized_financial_facts n ON n.id = l.normalized_fact_id WHERE n.company_id = :id)"
            ), {"id": company_id})
            raw_count, fact_count, normalized_count, lineage_count = counts.one()
            accessions = set(await connection.scalars(text(
                "SELECT accession_number FROM financial_facts WHERE company_id = :id"
            ), {"id": company_id}))
        assert (raw_count, fact_count, normalized_count, lineage_count) == (1, 2, 2, 2)
        assert accessions == {"0000000001-25-000001", "0000000001-25-000002"}
    finally:
        async with engine.begin() as connection:
            await connection.execute(text("DELETE FROM financial_fact_lineage WHERE normalized_fact_id IN (SELECT id FROM normalized_financial_facts WHERE company_id = :id)"), {"id": company_id})
            await connection.execute(text("DELETE FROM normalized_financial_facts WHERE company_id = :id"), {"id": company_id})
            await connection.execute(text("DELETE FROM financial_facts WHERE company_id = :id"), {"id": company_id})
            await connection.execute(text("DELETE FROM sec_raw_company_facts WHERE company_id = :id"), {"id": company_id})
            await connection.execute(text("DELETE FROM sec_provider_cache WHERE cache_key = 'companyfacts:0000000001'"))
            await connection.execute(text("DELETE FROM companies WHERE id = :id"), {"id": company_id})
        await engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_same_payload_imports_are_database_idempotent() -> None:
    engine = create_async_engine(DATABASE_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    company_id = uuid4()
    try:
        async with engine.begin() as connection:
            await connection.execute(text(
                "INSERT INTO companies (id, legal_name, status, created_at, updated_at) "
                "VALUES (:id, 'SEC concurrent fixture', 'ACTIVE', now(), now())"
            ), {"id": company_id})

        async def run_once() -> dict:
            async with factory() as session:
                return await SECCompanyFactsImportService(FixtureSECClient()).import_company(
                    session, company_id=company_id, cik="1"
                )

        results = await asyncio.gather(run_once(), run_once())
        assert sorted(result["imported_facts"] for result in results) == [0, 2]
        async with engine.connect() as connection:
            fact_count = await connection.scalar(text(
                "SELECT count(*) FROM financial_facts WHERE company_id = :id"
            ), {"id": company_id})
            raw_count = await connection.scalar(text(
                "SELECT count(*) FROM sec_raw_company_facts WHERE company_id = :id"
            ), {"id": company_id})
        assert (fact_count, raw_count) == (2, 1)
    finally:
        async with engine.begin() as connection:
            await connection.execute(text("DELETE FROM financial_fact_lineage WHERE normalized_fact_id IN (SELECT id FROM normalized_financial_facts WHERE company_id = :id)"), {"id": company_id})
            await connection.execute(text("DELETE FROM normalized_financial_facts WHERE company_id = :id"), {"id": company_id})
            await connection.execute(text("DELETE FROM financial_facts WHERE company_id = :id"), {"id": company_id})
            await connection.execute(text("DELETE FROM sec_raw_company_facts WHERE company_id = :id"), {"id": company_id})
            await connection.execute(text("DELETE FROM sec_provider_cache WHERE cache_key = 'companyfacts:0000000001'"))
            await connection.execute(text("DELETE FROM companies WHERE id = :id"), {"id": company_id})
        await engine.dispose()
