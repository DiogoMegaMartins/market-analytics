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
from app.services.valuation.comparison import compare_valuation_run_snapshots
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


@router.get("/valuation/companies/{company_id}/runs/{run_id}")
async def get_company_valuation_run(
    company_id: UUID,
    run_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return the immutable assumptions and result for one company-scoped run."""
    run = await session.scalar(
        select(ValuationRun).where(
            ValuationRun.id == run_id,
            ValuationRun.company_id == company_id,
        )
    )
    if run is None:
        # Do not disclose whether a run exists under another company.
        raise HTTPException(status_code=404, detail="Valuation run not found")
    return {
        "id": str(run.id),
        "company_id": str(run.company_id),
        "created_at": run.created_at.isoformat(),
        "created_by_user_id": str(run.created_by_user_id),
        "valuation_version": run.valuation_version,
        "method": run.method,
        "base_year": run.base_year,
        "currency": run.currency,
        "assumptions": run.assumptions,
        "result": run.result,
    }


@router.get(
    "/valuation/companies/{company_id}/runs/{baseline_run_id}/compare/{comparison_run_id}"
)
async def compare_company_valuation_runs(
    company_id: UUID,
    baseline_run_id: UUID,
    comparison_run_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Compare two immutable valuation snapshots within the same company."""
    if baseline_run_id == comparison_run_id:
        raise HTTPException(status_code=422, detail="Select two different valuation runs")
    runs = list((await session.scalars(
        select(ValuationRun).where(
            ValuationRun.company_id == company_id,
            ValuationRun.id.in_([baseline_run_id, comparison_run_id]),
        )
    )).all())
    by_id = {run.id: run for run in runs}
    baseline, comparison = by_id.get(baseline_run_id), by_id.get(comparison_run_id)
    if baseline is None or comparison is None:
        raise HTTPException(status_code=404, detail="Valuation run not found")
    try:
        result = compare_valuation_run_snapshots(
            {"id": baseline.id, "valuation_version": baseline.valuation_version,
             "method": baseline.method, "base_year": baseline.base_year,
             "currency": baseline.currency, "assumptions": baseline.assumptions,
             "result": baseline.result},
            {"id": comparison.id, "valuation_version": comparison.valuation_version,
             "method": comparison.method, "base_year": comparison.base_year,
             "currency": comparison.currency, "assumptions": comparison.assumptions,
             "result": comparison.result},
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"company_id": str(company_id), **result}
