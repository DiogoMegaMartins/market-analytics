"""Real PostgreSQL contract for immutable, tenant-scoped portfolio valuations."""
import os
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.endpoints.portfolio_valuation import PortfolioValuationCreate, create_portfolio_valuation
from app.models.auth import CompanyMembership, User
from app.models.identity import Company
from app.models.portfolio import Portfolio
from app.models.portfolio_valuation import PortfolioValuationSnapshot

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL is not configured")


@pytest.mark.asyncio
async def test_portfolio_valuation_is_idempotent_tenant_scoped_and_immutable():
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            company = Company(legal_name=f"Valuation tenant {uuid4()}")
            other = Company(legal_name=f"Other valuation tenant {uuid4()}")
            user = User(email=f"valuation-{uuid4()}@example.test", password_hash="not-used",
                        display_name="Portfolio Analyst", created_at=datetime.now(UTC))
            session.add_all([company, other, user])
            await session.flush()
            session.add(CompanyMembership(user_id=user.id, company_id=company.id, role="ANALYST", created_at=datetime.now(UTC)))
            portfolio = Portfolio(company_id=company.id, name="Performance", base_currency="EUR", status="ACTIVE",
                                  created_by_user_id=user.id, created_at=datetime.now(UTC), updated_at=datetime.now(UTC))
            session.add(portfolio)
            await session.commit()

            request = SimpleNamespace(state=SimpleNamespace(authenticated_user=user))
            data = PortfolioValuationCreate.model_validate({
                "valuation_date": date(2026, 1, 31), "market_value": "1250.50", "cash_value": "250",
                "currency": "EUR", "valuation_source": "BROKER_STATEMENT", "methodology": "Statement close",
                "idempotency_key": "jan-close",
            })
            created = await create_portfolio_valuation(company.id, portfolio.id, data, request, session)
            replay = await create_portfolio_valuation(company.id, portfolio.id, data, request, session)
            assert created["id"] == replay["id"] and replay["idempotent_replay"]
            assert created["total_value"] == "1500.50"

            changed = PortfolioValuationCreate.model_validate({
                **data.model_dump(mode="json"), "market_value": "1300", "cash_value": "250",
            })
            with pytest.raises(HTTPException) as conflict:
                await create_portfolio_valuation(company.id, portfolio.id, changed, request, session)
            assert conflict.value.status_code == 409
            with pytest.raises(HTTPException) as tenant:
                await create_portfolio_valuation(other.id, portfolio.id, data, request, session)
            assert tenant.value.status_code == 404

            persisted = await session.scalar(select(PortfolioValuationSnapshot).where(PortfolioValuationSnapshot.id == created["id"]))
            assert persisted is not None and persisted.market_value == Decimal("1250.5000000000")
            for statement in (
                "UPDATE portfolio_valuation_snapshots SET market_value = 999 WHERE id = :id",
                "DELETE FROM portfolio_valuation_snapshots WHERE id = :id",
            ):
                savepoint = await session.begin_nested()
                try:
                    with pytest.raises(DBAPIError):
                        await session.execute(text(statement), {"id": persisted.id})
                finally:
                    await savepoint.rollback()
            unchanged = await session.scalar(select(PortfolioValuationSnapshot).where(PortfolioValuationSnapshot.id == persisted.id))
            assert unchanged is not None and unchanged.market_value == Decimal("1250.5000000000")
    finally:
        await engine.dispose()
