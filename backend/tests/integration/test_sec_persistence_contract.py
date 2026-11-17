"""Synthetic, isolated PostgreSQL persistence tests; never production data."""
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
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
    cik = str(uuid4().int % 10000000000).zfill(10)
    fact_key = f"synthetic-fact-{uuid4()}"
    normalized_key = f"synthetic-normalized-{uuid4()}"
    try:
        async with factory() as session, session.begin():
            await session.execute(text(
                "INSERT INTO companies (id, legal_name, status, created_at, updated_at) "
                "VALUES (:id, 'Synthetic test company', 'ACTIVE', now(), now())"
            ), {"id": company_id})
            raw = SECRawCompanyFacts(
                id=raw_id, company_id=company_id, cik=cik, provider="SEC",
                source_url="https://example.test/sec", payload_hash=__import__("hashlib").sha256(str(company_id).encode()).hexdigest(),
                payload_text='{"synthetic": true}', retrieved_at=datetime.now(UTC),
            )
            fact = FinancialFact(
                id=fact_id, company_id=company_id, raw_record_id=raw_id, cik=cik,
                external_fact_key=fact_key, metric_id="FIN.REVENUE",
                taxonomy="us-gaap", tag="Revenue", value=Decimal(100), unit="USD",
                currency="USD", period_kind="ANNUAL", end_date=date(2024, 12, 31),
                accession_number=f"{cik}-24-000001", filed_at=date(2025, 2, 1),
                retrieved_at=datetime.now(UTC),
            )
            normalized = NormalizedFinancialFact(
                id=normalized_id, company_id=company_id, source_fact_id=fact_id,
                metric_id="FIN.REVENUE", value=Decimal(100), unit="USD", currency="USD",
                period_kind="ANNUAL", end_date=date(2024, 12, 31), normalized_key=normalized_key,
                available_at=datetime.now(UTC),
            )
            session.add(raw)
            await session.flush()
            session.add(fact)
            await session.flush()
            session.add(normalized)
            await session.flush()
            session.add(FinancialFactLineage(normalized_fact_id=normalized_id, source_fact_id=fact_id))
            await session.flush()
            with pytest.raises(IntegrityError):
                async with session.begin_nested():
                    session.add(FinancialFact(
                        company_id=company_id, raw_record_id=raw_id, cik=cik,
                        external_fact_key=fact_key, metric_id="FIN.REVENUE",
                        taxonomy="us-gaap", tag="Revenue", value=Decimal(101), unit="USD",
                        period_kind="ANNUAL", end_date=date(2024, 12, 31),
                        retrieved_at=datetime.now(UTC),
                    ))
                    await session.flush()
            # The failed savepoint has rolled back; the main transaction remains active.
            # A different accession remains a distinct restatement observation.
            session.add(FinancialFact(
                company_id=company_id, raw_record_id=raw_id, cik=cik,
                external_fact_key="synthetic-fact-restated", metric_id="FIN.REVENUE",
                taxonomy="us-gaap", tag="Revenue", value=Decimal(110), unit="USD",
                period_kind="ANNUAL", end_date=date(2024, 12, 31),
                accession_number=f"{cik}-25-000002", filed_at=date(2025, 3, 1),
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
        # Immutable SEC facts and lineage are append-only; CI provisions a fresh DB.
        await engine.dispose()
