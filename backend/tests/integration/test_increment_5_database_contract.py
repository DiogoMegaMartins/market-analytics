"""Opt-in real PostgreSQL checks for Increment 5.

Run only against a disposable database via TEST_DATABASE_URL after migrations.
"""
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL is not configured")


@pytest.mark.asyncio
async def test_increment_5_head_indexes_and_foreign_keys_exist() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            indexes = set(await connection.scalars(text(
                "SELECT indexname FROM pg_indexes WHERE schemaname = current_schema()"
            )))
            foreign_keys = await connection.scalar(text(
                "SELECT count(*) FROM information_schema.table_constraints "
                "WHERE constraint_type = 'FOREIGN KEY'"
            ))
        assert revision == "0021_valuation_run_immutability"
        assert "ix_financial_facts_company_metric_filed_accession" in indexes
        assert "ix_normalized_facts_company_metric_available" in indexes
        assert foreign_keys and foreign_keys > 0
    finally:
        await engine.dispose()
