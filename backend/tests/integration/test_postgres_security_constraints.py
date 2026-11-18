"""Optional real-PostgreSQL checks; enabled in CI with TEST_DATABASE_URL."""
import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL is not configured")


@pytest.mark.asyncio
async def test_database_is_migrated_to_security_head():
    engine = create_async_engine(DATABASE_URL)
    try:
        async with engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
        assert revision == "0022_portfolio_ledger"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_auth_audit_events_reject_update_and_delete():
    engine = create_async_engine(DATABASE_URL)
    first_id, second_id = uuid4(), uuid4()
    try:
        async with engine.connect() as connection:
            outer = await connection.begin()
            try:
                await connection.execute(
                    text("INSERT INTO auth_audit_events (id, event_type, success, created_at) "
                         "VALUES (:id, 'CI_IMMUTABILITY_TEST', true, now())"),
                    {"id": first_id},
                )
                await connection.execute(
                    text("INSERT INTO auth_audit_events (id, event_type, success, created_at) "
                         "VALUES (:id, 'CI_IMMUTABILITY_TEST', true, now())"),
                    {"id": second_id},
                )
                for statement, record_id in (
                    ("UPDATE auth_audit_events SET success = false WHERE id = :id", first_id),
                    ("DELETE FROM auth_audit_events WHERE id = :id", second_id),
                ):
                    savepoint = await connection.begin_nested()
                    try:
                        with pytest.raises(DBAPIError):
                            await connection.execute(text(statement), {"id": record_id})
                    finally:
                        await savepoint.rollback()
            finally:
                await outer.rollback()
    finally:
        await engine.dispose()
