"""Real PostgreSQL contract for portfolio ledger persistence and append-only enforcement."""
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

from app.api.v1.endpoints.portfolio import (
    PortfolioTransactionCreate,
    create_portfolio_transaction,
)
from app.models.auth import CompanyMembership, User
from app.models.identity import Asset, Company
from app.models.portfolio import Portfolio, PortfolioTransaction

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL is not configured")


@pytest.mark.asyncio
async def test_portfolio_transaction_ledger_is_tenant_linked_idempotent_and_immutable():
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            company = Company(legal_name=f"Portfolio tenant {uuid4()}")
            other_company = Company(legal_name=f"Other portfolio tenant {uuid4()}")
            user = User(
                email=f"portfolio-{uuid4()}@example.test", password_hash="not-used",
                display_name="Portfolio Analyst", created_at=datetime.now(UTC),
            )
            session.add_all([company, other_company, user])
            await session.flush()
            session.add(CompanyMembership(
                user_id=user.id, company_id=company.id, role="ANALYST", created_at=datetime.now(UTC),
            ))
            asset = Asset(company_id=company.id, asset_type="COMMON_STOCK", name="Synthetic asset")
            session.add(asset)
            await session.flush()

            portfolio = Portfolio(
                company_id=company.id, name="Long-term", base_currency="USD", status="ACTIVE",
                created_by_user_id=user.id, created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
            )
            session.add(portfolio)
            await session.commit()

            request = SimpleNamespace(state=SimpleNamespace(authenticated_user=user))
            payload = PortfolioTransactionCreate.model_validate({
                "transaction_type": "BUY", "trade_date": date(2026, 1, 5),
                "settlement_date": date(2026, 1, 7), "asset_id": str(asset.id),
                "quantity": "2.5", "unit_price": "10", "gross_amount": "25",
                "currency": "USD", "fees": "1", "taxes": "0",
                "idempotency_key": "synthetic-broker-fill-1",
                "external_reference": "synthetic-001",
            })
            created = await create_portfolio_transaction(
                company.id, portfolio.id, payload, request, session
            )
            replay = await create_portfolio_transaction(
                company.id, portfolio.id, payload, request, session
            )
            assert created["id"] == replay["id"]
            assert replay["idempotent_replay"] is True

            with pytest.raises(HTTPException) as conflict:
                await create_portfolio_transaction(
                    company.id, portfolio.id,
                    PortfolioTransactionCreate.model_validate({
                        **payload.model_dump(mode="json"), "gross_amount": "30",
                        "unit_price": "12",
                    }),
                    request, session,
                )
            assert conflict.value.status_code == 409

            with pytest.raises(HTTPException) as tenant_mismatch:
                await create_portfolio_transaction(
                    other_company.id, portfolio.id, payload, request, session
                )
            assert tenant_mismatch.value.status_code == 404

            persisted = await session.scalar(select(PortfolioTransaction).where(
                PortfolioTransaction.id == created["id"]
            ))
            assert persisted is not None
            assert persisted.gross_amount == Decimal("25.0000000000")
            assert persisted.company_id == company.id

            with pytest.raises(DBAPIError):
                async with session.begin_nested():
                    await session.execute(text(
                        "UPDATE portfolio_transactions SET gross_amount = 26 WHERE id = :id"
                    ), {"id": persisted.id})
            with pytest.raises(DBAPIError):
                async with session.begin_nested():
                    await session.execute(text(
                        "DELETE FROM portfolio_transactions WHERE id = :id"
                    ), {"id": persisted.id})
            unchanged = await session.scalar(select(PortfolioTransaction).where(
                PortfolioTransaction.id == persisted.id
            ))
            assert unchanged is not None
            assert unchanged.gross_amount == Decimal("25.0000000000")
    finally:
        await engine.dispose()
