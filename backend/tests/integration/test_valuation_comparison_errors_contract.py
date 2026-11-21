"""PostgreSQL HTTP contract for invalid valuation comparison requests."""
import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.dependencies import get_current_user
from app.api.v1.endpoints.valuation import router as valuation_router
from app.models.auth import CompanyMembership, User
from app.models.financial_data import ValuationRun
from app.models.identity import Company
from app.platform.database.session import get_db_session

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL is not configured")


def _result(value: str) -> dict:
    scenarios = {}
    for scenario, multiplier in (("BEAR", 0.8), ("BASE", 1.0), ("BULL", 1.2)):
        enterprise_value = float(value) * multiplier
        equity_value = enterprise_value - 100
        scenarios[scenario] = {
            "enterprise_value": str(enterprise_value),
            "equity_value": str(equity_value),
            "value_per_share": str(equity_value / 50),
            "present_value_explicit_fcff": "200",
            "present_value_terminal_value": str(enterprise_value - 200),
        }
    return {"scenarios": scenarios}


@pytest.mark.asyncio
async def test_comparison_http_rejects_same_and_incompatible_runs():
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            company = Company(legal_name=f"Invalid comparison {uuid4()}")
            user = User(
                email=f"valuation-invalid-compare-{uuid4()}@example.test",
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
            common = {
                "company_id": company.id,
                "created_by_user_id": user.id,
                "valuation_version": "fcff-dcf-v1",
                "method": "FCFF_DCF",
                "currency": "USD",
                "assumptions": {"wacc": "0.09", "terminal_growth": "0.025"},
                "result": _result("1000"),
                "created_at": datetime.now(UTC),
            }
            baseline = ValuationRun(base_year=2024, **common)
            incompatible = ValuationRun(
                base_year=2025,
                assumptions={"wacc": "0.09", "terminal_growth": "0.025"},
                result=_result("1100"),
                **{key: value for key, value in common.items() if key not in {"assumptions", "result"}},
            )
            session.add_all([baseline, incompatible])
            await session.commit()

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
                prefix = f"/api/v1/valuation/companies/{company.id}/runs"
                same = await client.get(
                    f"{prefix}/{baseline.id}/compare/{baseline.id}"
                )
                mismatched = await client.get(
                    f"{prefix}/{baseline.id}/compare/{incompatible.id}"
                )

            assert same.status_code == 422
            assert same.json()["detail"] == "Select two different valuation runs"
            assert mismatched.status_code == 422
            assert "incompatible base_year" in mismatched.json()["detail"]
    finally:
        await engine.dispose()
