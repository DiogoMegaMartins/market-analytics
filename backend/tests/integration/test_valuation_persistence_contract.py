"""Real-PostgreSQL contract for the company-scoped FCFF DCF API and history."""
import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.requests import Request

from app.api.v1.dependencies import get_current_user, require_company_access
from app.api.v1.endpoints.valuation import (
    DCFValuationInput,
    create_company_dcf_valuation,
    get_company_valuation_history,
    get_company_valuation_run,
    get_company_valuation_run,
)
from app.api.v1.endpoints.valuation import (
    router as valuation_router,
)
from app.models.auth import CompanyMembership, User
from app.models.financial_data import ValuationRun
from app.models.identity import Company
from app.platform.database.session import get_db_session

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL is not configured")


def _request(company_id, *, method: str = "POST") -> Request:
    path = f"/api/v1/valuation/companies/{company_id}/dcf"
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345),
        "path_params": {"company_id": str(company_id)},
    }
    return Request(scope)


def _period(year: int, *, revenue: str) -> dict:
    return {
        "year": year,
        "revenue": revenue,
        "ebit_margin": "0.20",
        "tax_rate": "0.25",
        "da": "40",
        "capex": "50",
        "change_nwc": "10",
    }


def _payload() -> DCFValuationInput:
    return DCFValuationInput.model_validate({
        "base_year": 2024,
        "currency": "USD",
        "wacc": "0.09",
        "terminal_growth": "0.025",
        "net_debt": "100",
        "diluted_shares": "50",
        "scenarios": {
            "BEAR": [_period(2025, revenue="900")],
            "BASE": [_period(2025, revenue="1000")],
            "BULL": [_period(2025, revenue="1100")],
        },
    })


@pytest.mark.asyncio
async def test_company_dcf_creation_persists_immutable_run_and_returns_history() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            company = Company(legal_name=f"Valuation integration {uuid4()}")
            user = User(
                email=f"valuation-{uuid4()}@example.test",
                password_hash="not-used",
                display_name="Valuation Analyst",
                created_at=datetime.now(UTC),
            )
            session.add_all([company, user])
            await session.flush()
            session.add(CompanyMembership(
                user_id=user.id,
                company_id=company.id,
                role="ANALYST",
                created_at=datetime.now(UTC),
            ))
            await session.flush()

            request = _request(company.id)
            # Exercise the same tenant/role guard attached to the live router.
            await require_company_access(request, current_user=user, session=session)
            response = await create_company_dcf_valuation(
                company.id, _payload(), request, session
            )

            assert response["company_id"] == str(company.id)
            assert response["valuation_version"] == "fcff-dcf-v1"
            assert response["result"]["method"] == "FCFF_DCF"
            assert response["result"]["investment_recommendation"] is None

            persisted = await session.scalar(
                select(ValuationRun).where(ValuationRun.id == response["id"])
            )
            assert persisted is not None
            assert persisted.company_id == company.id
            assert persisted.created_by_user_id == user.id
            assert persisted.assumptions["scenarios"]["BASE"][0]["revenue"] == "1000"
            assert persisted.result == response["result"]

            history = await get_company_valuation_history(
                company.id, limit=20, session=session
            )
            assert len(history["valuations"]) == 1
            assert history["valuations"][0]["id"] == response["id"]
            assert history["valuations"][0]["method"] == "FCFF_DCF"

            detail = await get_company_valuation_run(
                company.id, UUID(response["id"]), session
            )
            assert detail["assumptions"] == persisted.assumptions
            assert detail["result"] == persisted.result
            assert detail["created_by_user_id"] == str(user.id)

            # PostgreSQL must reject both mutation paths, without poisoning the
            # surrounding session transaction (each expected failure is isolated).
            with pytest.raises(DBAPIError):
                async with session.begin_nested():
                    await session.execute(
                        text("UPDATE valuation_runs SET currency = 'EUR' WHERE id = :id"),
                        {"id": response["id"]},
                    )
            with pytest.raises(DBAPIError):
                async with session.begin_nested():
                    await session.execute(
                        text("DELETE FROM valuation_runs WHERE id = :id"),
                        {"id": response["id"]},
                    )
            still_persisted = await session.scalar(
                select(ValuationRun).where(ValuationRun.id == response["id"])
            )
            assert still_persisted is not None
            assert still_persisted.currency == "USD"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_company_dcf_access_is_tenant_scoped() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            own_company = Company(legal_name=f"Valuation own {uuid4()}")
            other_company = Company(legal_name=f"Valuation other {uuid4()}")
            user = User(
                email=f"valuation-scope-{uuid4()}@example.test",
                password_hash="not-used",
                display_name="Scoped Analyst",
                created_at=datetime.now(UTC),
            )
            session.add_all([own_company, other_company, user])
            await session.flush()
            session.add(CompanyMembership(
                user_id=user.id,
                company_id=own_company.id,
                role="ANALYST",
                created_at=datetime.now(UTC),
            ))
            await session.flush()
            foreign_run = ValuationRun(
                company_id=other_company.id,
                created_by_user_id=user.id,
                valuation_version="fcff-dcf-v1",
                method="FCFF_DCF",
                base_year=2024,
                currency="USD",
                assumptions={"scenarios": {"BASE": []}},
                result={"method": "FCFF_DCF"},
                created_at=datetime.now(UTC),
            )
            session.add(foreign_run)
            await session.flush()

            with pytest.raises(HTTPException) as run_error:
                await get_company_valuation_run(
                    own_company.id, foreign_run.id, session
                )
            assert run_error.value.status_code == 404

            allowed = _request(own_company.id)
            await require_company_access(allowed, current_user=user, session=session)
            assert allowed.state.company_role == "ANALYST"

            denied = _request(other_company.id)
            with pytest.raises(HTTPException) as error:
                await require_company_access(denied, current_user=user, session=session)
            assert error.value.status_code == 404

            # Exercise the actual GET route so its router-level dependency is covered.
            app = FastAPI()
            app.include_router(valuation_router, prefix="/api/v1")

            async def override_user():
                return user

            async def override_session():
                yield session

            app.dependency_overrides[get_current_user] = override_user
            app.dependency_overrides[get_db_session] = override_session
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                response = await client.get(
                    f"/api/v1/valuation/companies/{other_company.id}/history"
                )
            assert response.status_code == 404
    finally:
        await engine.dispose()
