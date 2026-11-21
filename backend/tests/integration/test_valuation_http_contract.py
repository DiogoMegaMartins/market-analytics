"""HTTP-level PostgreSQL contract for company DCF creation and write authorization."""
import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.dependencies import get_current_user
from app.api.v1.endpoints.valuation import router as valuation_router
from app.models.auth import CompanyMembership, User
from app.models.financial_data import ValuationRun
from app.models.identity import Company
from app.platform.database.session import get_db_session

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL is not configured")


def _payload() -> dict:
    period = {
        "year": 2025,
        "revenue": "1000",
        "ebit_margin": "0.20",
        "tax_rate": "0.25",
        "da": "40",
        "capex": "50",
        "change_nwc": "10",
    }
    return {
        "base_year": 2024,
        "currency": "USD",
        "wacc": "0.09",
        "terminal_growth": "0.025",
        "net_debt": "100",
        "diluted_shares": "50",
        "scenarios": {
            "BEAR": [period],
            "BASE": [period],
            "BULL": [period],
        },
    }


@pytest.mark.asyncio
async def test_dcf_post_http_contract_validates_authorizes_and_persists():
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            company = Company(legal_name=f"DCF HTTP contract {uuid4()}")
            analyst = User(
                email=f"dcf-http-analyst-{uuid4()}@example.test",
                password_hash="not-used",
                display_name="DCF Analyst",
                created_at=datetime.now(UTC),
            )
            viewer = User(
                email=f"dcf-http-viewer-{uuid4()}@example.test",
                password_hash="not-used",
                display_name="DCF Viewer",
                created_at=datetime.now(UTC),
            )
            session.add_all([company, analyst, viewer])
            await session.flush()
            session.add_all([
                CompanyMembership(
                    user_id=analyst.id,
                    company_id=company.id,
                    role="ANALYST",
                    created_at=datetime.now(UTC),
                ),
                CompanyMembership(
                    user_id=viewer.id,
                    company_id=company.id,
                    role="REVIEWER",
                    created_at=datetime.now(UTC),
                ),
            ])
            await session.commit()

            app = FastAPI()
            app.include_router(valuation_router, prefix="/api/v1")
            active_user = {"value": analyst}

            async def override_user():
                return active_user["value"]

            async def override_session():
                yield session

            app.dependency_overrides[get_current_user] = override_user
            app.dependency_overrides[get_db_session] = override_session

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                path = f"/api/v1/valuation/companies/{company.id}/dcf"
                invalid = _payload()
                invalid["unexpected"] = "must be rejected"
                invalid_response = await client.post(path, json=invalid)
                assert invalid_response.status_code == 422

                created = await client.post(path, json=_payload())
                assert created.status_code == 201
                body = created.json()
                assert body["company_id"] == str(company.id)
                assert body["valuation_version"] == "fcff-dcf-v1"
                assert body["result"]["method"] == "FCFF_DCF"
                assert body["result"]["investment_recommendation"] is None

                persisted = await session.scalar(
                    select(ValuationRun).where(ValuationRun.id == body["id"])
                )
                assert persisted is not None
                assert persisted.company_id == company.id
                assert persisted.created_by_user_id == analyst.id

                active_user["value"] = viewer
                denied = await client.post(path, json=_payload())
                assert denied.status_code == 403

            count = await session.scalar(
                select(func.count()).select_from(ValuationRun).where(
                    ValuationRun.company_id == company.id
                )
            )
            assert count == 1
    finally:
        await engine.dispose()
