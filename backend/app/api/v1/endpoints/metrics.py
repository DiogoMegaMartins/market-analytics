from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_company_access
from app.domain.fact_resolution import ResolutionPolicy
from app.models.financial_data import FinancialMetricResult, FinancialMetricRun
from app.models.identity import Company
from app.platform.database.session import get_db_session
from app.services.financial_data.quarter_derivation import FinancialQuarterDerivationService
from app.services.metrics.evolution import build_financial_evolution
from app.services.metrics.persistence import FinancialMetricsService

router = APIRouter(tags=["financial-metrics"], dependencies=[Depends(require_company_access)])


@router.post("/metrics/companies/{company_id}/annual/{fiscal_year}")
async def calculate_company_annual_metrics(
    company_id: UUID,
    fiscal_year: int,
    policy: ResolutionPolicy = Query(default=ResolutionPolicy.LATEST_RESTATED),
    as_known_at: date | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    if fiscal_year < 1900 or fiscal_year > 2200:
        raise HTTPException(status_code=422, detail="Invalid fiscal year")
    if await session.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    try:
        result = await FinancialMetricsService().calculate_annual(
            session, company_id=company_id, fiscal_year=fiscal_year,
            policy=policy, as_known_at=as_known_at,
        )
        await session.commit()
        return result
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        await session.rollback()
        raise


@router.get("/metrics/companies/{company_id}/annual/{fiscal_year}/history")
async def get_company_annual_metrics(
    company_id: UUID, fiscal_year: int,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    runs = list((await session.scalars(select(FinancialMetricRun).where(
        FinancialMetricRun.company_id == company_id,
        FinancialMetricRun.fiscal_year == fiscal_year,
    ).order_by(FinancialMetricRun.created_at.desc()))).all())
    if not runs:
        return {"company_id": str(company_id), "fiscal_year": fiscal_year, "runs": []}
    results = list((await session.scalars(select(FinancialMetricResult).where(
        FinancialMetricResult.run_id == runs[0].id
    ).order_by(FinancialMetricResult.metric_id))).all())
    return {
        "company_id": str(company_id), "fiscal_year": fiscal_year,
        "run_id": str(runs[0].id), "engine_version": runs[0].engine_version,
        "resolution_policy": runs[0].resolution_policy, "status": runs[0].status,
        "metrics": [{"metric_id": r.metric_id, "value": str(r.value) if r.value is not None else None,
                     "unit": r.unit, "status": r.status, "reason": r.reason} for r in results],
    }


@router.post("/metrics/companies/{company_id}/derive-quarters/{fiscal_year}")
async def derive_company_quarters(
    company_id: UUID, fiscal_year: int,
    as_known_at: date | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    if await session.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    try:
        result = await FinancialQuarterDerivationService().derive_company_year(
            session, company_id=company_id, fiscal_year=fiscal_year,
            as_known_at=as_known_at,
        )
        await session.commit()
        return result
    except Exception:
        await session.rollback()
        raise


@router.get("/metrics/companies/{company_id}/evolution")
async def get_company_financial_evolution(
    company_id: UUID,
    from_fiscal_year: int = Query(..., ge=1900, le=2200),
    to_fiscal_year: int = Query(..., ge=1900, le=2200),
    materiality_threshold_pct: Decimal = Query(default=Decimal(10), gt=0, le=1000),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Compare persisted annual metric runs and flag heuristic material changes."""
    if from_fiscal_year >= to_fiscal_year:
        raise HTTPException(status_code=422, detail="from_fiscal_year must be earlier than to_fiscal_year")
    if to_fiscal_year - from_fiscal_year > 15:
        raise HTTPException(status_code=422, detail="Fiscal year comparison window cannot exceed 15 years")
    if await session.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")

    years = [from_fiscal_year, to_fiscal_year]
    runs = list((await session.scalars(
        select(FinancialMetricRun)
        .where(
            FinancialMetricRun.company_id == company_id,
            FinancialMetricRun.fiscal_year.in_(years),
        )
        .order_by(FinancialMetricRun.fiscal_year, FinancialMetricRun.created_at.desc(),
                  FinancialMetricRun.id.desc())
    )).all())
    latest_by_year = {}
    for run in runs:
        latest_by_year.setdefault(run.fiscal_year, run)

    metrics_by_year = {year: [] for year in years}
    for year, run in latest_by_year.items():
        results = list((await session.scalars(
            select(FinancialMetricResult)
            .where(FinancialMetricResult.run_id == run.id)
            .order_by(FinancialMetricResult.metric_id)
        )).all())
        metrics_by_year[year] = [
            {"metric_id": item.metric_id,
             "value": str(item.value) if item.value is not None else None,
             "unit": item.unit, "status": item.status, "reason": item.reason}
            for item in results
        ]

    if from_fiscal_year not in latest_by_year or to_fiscal_year not in latest_by_year:
        missing = [year for year in years if year not in latest_by_year]
        return {
            "company_id": str(company_id),
            "comparison": {"from_fiscal_year": from_fiscal_year, "to_fiscal_year": to_fiscal_year},
            "status": "INSUFFICIENT_DATA",
            "missing_fiscal_years": missing,
            "available_fiscal_years": sorted(latest_by_year),
            "analyst_review_required": True,
        }

    result = build_financial_evolution(
        company_id=str(company_id),
        from_fiscal_year=from_fiscal_year,
        to_fiscal_year=to_fiscal_year,
        previous_metrics=metrics_by_year[from_fiscal_year],
        current_metrics=metrics_by_year[to_fiscal_year],
        threshold_pct=materiality_threshold_pct,
    )
    result["status"] = "COMPLETED"
    result["metric_runs"] = {
        str(year): {
            "run_id": str(latest_by_year[year].id),
            "engine_version": latest_by_year[year].engine_version,
            "resolution_policy": latest_by_year[year].resolution_policy,
            "status": latest_by_year[year].status,
            "created_at": latest_by_year[year].created_at.isoformat(),
        }
        for year in years
    }
    return result
