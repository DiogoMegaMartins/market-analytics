from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_company_access
from app.models.financial_data import ValuationRun
from app.models.identity import Company
from app.platform.database.session import get_db_session
from app.services.valuation.dcf import calculate_fcff_dcf

router = APIRouter(tags=["valuation"], dependencies=[Depends(require_company_access)])


class ForecastPeriodInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    year: int = Field(ge=1900, le=2200)
    revenue: Decimal
    ebit_margin: Decimal
    tax_rate: Decimal
    da: Decimal
    capex: Decimal
    change_nwc: Decimal


class DCFValuationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_year: int = Field(ge=1900, le=2200)
    currency: str = Field(pattern="^[A-Z]{3}$")
    scenarios: dict[str, list[ForecastPeriodInput]]
    wacc: Decimal
    terminal_growth: Decimal
    net_debt: Decimal
    diluted_shares: Decimal


@router.post(
    "/valuation/companies/{company_id}/dcf",
    status_code=status.HTTP_201_CREATED,
)
async def create_company_dcf_valuation(
    company_id: UUID,
    payload: DCFValuationInput,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    assumptions = payload.model_dump(mode="json")
    try:
        result = calculate_fcff_dcf(**assumptions)
    except (ValueError, ArithmeticError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    created_at = datetime.now(UTC)
    run = ValuationRun(
        company_id=company_id,
        created_by_user_id=request.state.authenticated_user.id,
        valuation_version=result["valuation_version"],
        method=result["method"],
        base_year=payload.base_year,
        currency=payload.currency,
        assumptions=assumptions,
        result=result,
        created_at=created_at,
    )
    session.add(run)
    await session.commit()
    return {
        "id": str(run.id),
        "company_id": str(company_id),
        "created_at": created_at.isoformat(),
        "valuation_version": run.valuation_version,
        "result": result,
    }


@router.get("/valuation/companies/{company_id}/history")
async def get_company_valuation_history(
    company_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    if await session.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    runs = list((await session.scalars(
        select(ValuationRun)
        .where(ValuationRun.company_id == company_id)
        .order_by(ValuationRun.created_at.desc(), ValuationRun.id.desc())
        .limit(limit)
    )).all())
    return {
        "company_id": str(company_id),
        "valuations": [
            {
                "id": str(run.id),
                "created_at": run.created_at.isoformat(),
                "valuation_version": run.valuation_version,
                "method": run.method,
                "base_year": run.base_year,
                "currency": run.currency,
                "result": run.result,
            }
            for run in runs
        ],
    }
