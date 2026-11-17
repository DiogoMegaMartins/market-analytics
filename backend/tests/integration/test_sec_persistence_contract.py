"""Synthetic, isolated PostgreSQL persistence tests; never production data."""
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.financial_data import (
    FinancialFact,
    FinancialFactLineage,
    NormalizedFinancialFact,
    SECRawCompanyFacts,
)

DATABASE_URL = __import__("os").environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL is not configured")


@pytest.mark.asyncio
async def test_sec_raw_normalized_lineage_restatement_idempotency_and_rollback() -> None:
    engine = create_async_engine(DATABASE_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    company_id = uuid4()
    raw_id = uuid4()
    fact_id = uuid4()
    normalized_id = uuid4()
    try:
        async with factory() as session, session.begin():
            await session.execute(text(
                "INSERT INTO companies (id, legal_name, status, created_at, updated_at) "
                "VALUES (:id, 'Synthetic test company', 'ACTIVE', now(), now())"
            ), {"id": company_id})
            raw = SECRawCompanyFacts(
                id=raw_id, company_id=company_id, cik="0000000001", provider="SEC",
                source_url="https://example.test/sec", payload_hash="a" * 64,
                payload_text='{"synthetic": true}', retrieved_at=datetime.now(UTC),
            )
            fact = FinancialFact(
                id=fact_id, company_id=company_id, raw_record_id=raw_id, cik="0000000001",
                external_fact_key="synthetic-fact-1", metric_id="FIN.REVENUE",
                taxonomy="us-gaap", tag="Revenue", value=Decimal(100), unit="USD",
                currency="USD", period_kind="ANNUAL", end_date=date(2024, 12, 31),
                accession_number="0000000001-24-000001", filed_at=date(2025, 2, 1),
                retrieved_at=datetime.now(UTC),
            )
            normalized = NormalizedFinancialFact(
                id=normalized_id, company_id=company_id, source_fact_id=fact_id,
                metric_id="FIN.REVENUE", value=Decimal(100), unit="USD", currency="USD",
                period_kind="ANNUAL", end_date=date(2024, 12, 31), normalized_key="synthetic-normalized-1",
                available_at=datetime.now(UTC),
            )
            session.add_all([raw, fact, normalized])
            await session.flush()
            session.add(FinancialFactLineage(normalized_fact_id=normalized_id, source_fact_id=fact_id))
            with pytest.raises(IntegrityError):
                async with session.begin_nested():
                    session.add(FinancialFact(
                        company_id=company_id, raw_record_id=raw_id, cik="0000000001",
                        external_fact_key="synthetic-fact-1", metric_id="FIN.REVENUE",
                        taxonomy="us-gaap", tag="Revenue", value=Decimal(101), unit="USD",
                        period_kind="ANNUAL", end_date=date(2024, 12, 31),
                        retrieved_at=datetime.now(UTC),
                    ))
                    await session.flush()
            # The failed savepoint has rolled back; the main transaction remains active.
            # A different accession remains a distinct restatement observation.
            session.add(FinancialFact(
                company_id=company_id, raw_record_id=raw_id, cik="0000000001",
                external_fact_key="synthetic-fact-restated", metric_id="FIN.REVENUE",
                taxonomy="us-gaap", tag="Revenue", value=Decimal(110), unit="USD",
                period_kind="ANNUAL", end_date=date(2024, 12, 31),
                accession_number="0000000001-25-000002", filed_at=date(2025, 3, 1),
                retrieved_at=datetime.now(UTC),
            ))
            with pytest.raises(DBAPIError):
                async with session.begin_nested():
                    await session.execute(text("UPDATE financial_facts SET value = 999 WHERE id = :id"), {"id": fact_id})
            original_value = await session.scalar(text("SELECT value FROM financial_facts WHERE id = :id"), {"id": fact_id})
            persisted_count = await session.scalar(text(
                "SELECT count(*) FROM financial_facts WHERE company_id = :id"
            ), {"id": company_id})
            assert original_value == Decimal(100)
            assert persisted_count == 2
        async with engine.connect() as connection:
            count = await connection.scalar(text("SELECT count(*) FROM financial_fact_lineage WHERE normalized_fact_id = :id"), {"id": normalized_id})
            restatements = await connection.scalar(text("SELECT count(*) FROM financial_facts WHERE company_id = :id AND metric_id = 'FIN.REVENUE'"), {"id": company_id})
            assert count == 1
            assert restatements == 2
    finally:
        async with engine.begin() as connection:
            await connection.execute(delete(FinancialFactLineage).where(FinancialFactLineage.normalized_fact_id == normalized_id))
            await connection.execute(delete(NormalizedFinancialFact).where(NormalizedFinancialFact.id == normalized_id))
            await connection.execute(delete(FinancialFact).where(FinancialFact.company_id == company_id))
            await connection.execute(delete(SECRawCompanyFacts).where(SECRawCompanyFacts.id == raw_id))
            await connection.execute(text("DELETE FROM companies WHERE id = :id"), {"id": company_id})
        await engine.dispose()
