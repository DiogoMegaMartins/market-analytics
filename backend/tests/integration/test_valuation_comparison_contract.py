"""PostgreSQL contract for persisted valuation run comparison and tenant isolation."""
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


def _result(revenue: str) -> dict:
    scenarios = {}
    for scenario, multiplier in (("BEAR", "0.8"), ("BASE", "1"), ("BULL", "1.2")):
        value = str(float(revenue) * float(multiplier))
        scenarios[scenario] = {
            "enterprise_value": value,
            "equity_value": str(float(value) - 100),
            "value_per_share": str((float(value) - 100) / 50),
            "present_value_explicit_fcff": "200",
            "present_value_terminal_value": str(float(value) - 200),
        }
    return {"scenarios": scenarios}


@pytest.mark.asyncio
async def test_comparison_endpoint_is_read_only_and_hides_foreign_runs():
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            company = Company(legal_name=f"Valuation comparison {uuid4()}")
            other_company = Company(legal_name=f"Valuation comparison other {uuid4()}")
            user = User(
                email=f"valuation-compare-{uuid4()}@example.test",
                password_hash="not-used",
                display_name="Valuation Analyst",
                created_at=datetime.now(UTC),
            )
            session.add_all([company, other_company, user])
            await session.flush()
            session.add(
                CompanyMembership(
                    user_id=user.id,
                    company_id=company.id,
                    role="ANALYST",
                    created_at=datetime.now(UTC),
                )
            )
            common = {
                "valuation_version": "fcff-dcf-v1",
                "method": "FCFF_DCF",
                "base_year": 2024,
                "currency": "USD",
                "created_at": datetime.now(UTC),
            }
            baseline = ValuationRun(
                company_id=company.id,
                created_by_user_id=user.id,
                assumptions={"wacc": "0.09", "revenue": "1000", "scenarios": {"BASE": [{"year": 2025, "revenue": "1000"}]}},
                result=_result("1000"),
                **common,
            )
            comparison = ValuationRun(
                company_id=company.id,
                created_by_user_id=user.id,
                assumptions={"wacc": "0.08", "revenue": "1200", "scenarios": {"BASE": [{"year": 2025, "revenue": "1200"}]}},
                result=_result("1200"),
                **common,
            )
            foreign = ValuationRun(
                company_id=other_company.id,
                created_by_user_id=user.id,
                assumptions={"wacc": "0.09", "revenue": "900"},
                result=_result("900"),
                **common,
            )
            session.add_all([baseline, comparison, foreign])
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
                response = await client.get(
                    f"/api/v1/valuation/companies/{company.id}/runs/"
                    f"{baseline.id}/compare/{comparison.id}"
                )
                hidden = await client.get(
                    f"/api/v1/valuation/companies/{company.id}/runs/"
                    f"{baseline.id}/compare/{foreign.id}"
                )
            assert response.status_code == 200
            data = response.json()
            assert data["scenarios"]["BASE"]["enterprise_value"]["percentage"] == "20.0"
            assert data["changed_assumption_fields"] == ["revenue", "scenarios", "wacc"]
            assert data["changed_assumption_paths"] == [
                "revenue", "scenarios.BASE.0.revenue", "wacc"
            ]
            assert data["assumption_differences"][1] == {
                "path": "scenarios.BASE.0.revenue",
                "json_pointer": "/scenarios/BASE/0/revenue",
                "baseline": "1000",
                "comparison": "1200",
                "baseline_present": True,
                "comparison_present": True,
            }
            assert hidden.status_code == 404
            await session.refresh(baseline)
            await session.refresh(comparison)
            assert baseline.result == _result("1000")
            assert comparison.result == _result("1200")
    finally:
        await engine.dispose()
