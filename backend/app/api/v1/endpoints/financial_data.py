from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_company_access
from app.models.financial_data import FinancialFact, NormalizedFinancialFact
from app.models.identity import Asset, AssetIdentifier, Company, IdentifierType
from app.platform.database.session import get_db_session
from app.providers.sec.client import SECProviderError
from app.services.financial_data.sec_company_facts import SECCompanyFactsImportService
from app.services.metrics.company_reconciliation import reconcile_company_against_reference
from app.services.metrics.historical import QuarterlyObservation, calculate_ttm

router = APIRouter(tags=["financial-data"], dependencies=[Depends(require_company_access)])


@router.post("/financial-data/assets/{asset_id}/import/sec-company-facts")
async def import_sec_company_facts(
    asset_id: UUID, session: AsyncSession = Depends(get_db_session)
) -> dict:
    asset = await session.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    cik_identifier = await session.scalar(select(AssetIdentifier).where(
        AssetIdentifier.company_id == asset.company_id,
        AssetIdentifier.identifier_type == IdentifierType.CIK.value,
        AssetIdentifier.verification_status == "VERIFIED",
    ))
    if cik_identifier is None:
        raise HTTPException(status_code=409, detail="Asset company has no verified SEC CIK")
    try:
        return await SECCompanyFactsImportService().import_company(
            session, company_id=asset.company_id, cik=cik_identifier.value
        )
    except SECProviderError as exc:
        await session.rollback()
        raise HTTPException(status_code=502, detail="SEC Company Facts provider unavailable") from exc
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc

from app.domain.fact_resolution import ResolutionPolicy
from app.services.financial_data.resolution import FinancialFactResolutionService
from app.services.metrics.historical import detect_restatements


@router.get("/financial-data/companies/{company_id}/facts")
async def get_resolved_financial_facts(
    company_id: UUID,
    policy: ResolutionPolicy = Query(default=ResolutionPolicy.LATEST_RESTATED),
    as_known_at: date | None = Query(default=None),
    metric_id: str | None = Query(default=None, max_length=80),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    try:
        facts = await FinancialFactResolutionService().resolve(
            session, company_id=company_id, policy=policy,
            as_known_at=as_known_at, metric_id=metric_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "company_id": str(company_id), "policy": policy.value,
        "as_known_at": as_known_at.isoformat() if as_known_at else None,
        "facts": [
            {
                "id": str(fact.id), "metric_id": fact.metric_id,
                "value": str(fact.value), "unit": fact.unit,
                "currency": fact.currency, "period_kind": fact.period_kind,
                "fiscal_year": fact.fiscal_year, "fiscal_period": fact.fiscal_period,
                "start_date": fact.start_date.isoformat() if fact.start_date else None,
                "end_date": fact.end_date.isoformat(),
                "form": fact.form, "filed_at": fact.filed_at.isoformat() if fact.filed_at else None,
                "accession_number": fact.accession_number,
            }
            for fact in facts
        ],
    }


@router.get("/financial-data/companies/{company_id}/restatements")
async def get_company_restatements(
    company_id: UUID,
    metric_id: str | None = Query(default=None, max_length=80),
    materiality_threshold: Decimal = Query(default=Decimal("0.05"), ge=0, le=1),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    if await session.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    stmt = select(FinancialFact).where(FinancialFact.company_id == company_id)
    if metric_id:
        stmt = stmt.where(FinancialFact.metric_id == metric_id)
    facts = list((await session.scalars(stmt)).all())
    changes = detect_restatements(facts, materiality_threshold=materiality_threshold)
    return {
        "company_id": str(company_id),
        "materiality_threshold": str(materiality_threshold),
        "threshold_is_heuristic": True,
        "restatements": [
            {
                "metric_id": item.metric_id, "fiscal_year": item.fiscal_year,
                "fiscal_period": item.fiscal_period,
                "old_value": str(item.old_value), "new_value": str(item.new_value),
                "absolute_change": str(item.absolute_change),
                "relative_change": str(item.relative_change) if item.relative_change is not None else None,
                "old_filed_at": item.old_filed_at.isoformat() if item.old_filed_at else None,
                "new_filed_at": item.new_filed_at.isoformat() if item.new_filed_at else None,
                "material": item.material,
            }
            for item in changes
        ],
    }


@router.get("/metrics/companies/{company_id}/ttm")
async def get_company_ttm(
    company_id: UUID,
    metric_id: str = Query(default="FIN.REVENUE", max_length=80),
    as_known_at: date | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    if await session.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    stmt = select(NormalizedFinancialFact).where(
        NormalizedFinancialFact.company_id == company_id,
        NormalizedFinancialFact.metric_id == metric_id,
        NormalizedFinancialFact.period_kind == "QUARTER",
    )
    rows = list((await session.scalars(stmt)).all())
    if as_known_at is not None:
        rows = [row for row in rows if row.filed_at is not None and row.filed_at <= as_known_at]
    grouped: dict[tuple, list[NormalizedFinancialFact]] = {}
    for row in rows:
        grouped.setdefault((row.start_date, row.end_date, row.unit, row.currency), []).append(row)
    selected = []
    for candidates in grouped.values():
        candidates.sort(key=lambda row: (row.filed_at or date.min, row.available_at), reverse=True)
        selected.append(candidates[0])
    selected.sort(key=lambda row: row.end_date)
    if len(selected) < 4:
        raise HTTPException(status_code=409, detail="Four eligible standalone quarters are required for TTM")
    latest_four = selected[-4:]
    try:
        result = calculate_ttm([
            QuarterlyObservation(
                metric_id=row.metric_id, value=row.value, unit=row.unit, currency=row.currency,
                start_date=row.start_date, end_date=row.end_date,
                fiscal_year=row.fiscal_year, fiscal_period=row.fiscal_period,
            )
            for row in latest_four if row.start_date is not None
        ])
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "company_id": str(company_id), "metric_id": result.metric_id,
        "value": str(result.value), "unit": result.unit, "currency": result.currency,
        "period_start": result.period_start.isoformat(), "period_end": result.period_end.isoformat(),
        "quarter_count": result.quarter_count, "as_known_at": as_known_at.isoformat() if as_known_at else None,
    }


from app.services.metrics.reference_validation import ReconciliationStatus


@router.get("/financial-data/companies/{company_id}/reconcile-reference")
async def reconcile_company_reference(
    company_id: UUID,
    ticker: str = Query(..., min_length=1, max_length=12),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    try:
        reference, results = await reconcile_company_against_reference(
            session, company_id=company_id, ticker=ticker,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="No curated reference for ticker") from exc
    except LookupError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "company_id": str(company_id),
        "ticker": reference["ticker"],
        "fiscal_year": reference["fiscal_year"],
        "period_end": reference["period_end"],
        "reference_source": {
            "name": reference["source_name"], "url": reference["source_url"],
        },
        "results": [
            {
                "metric_id": item.metric_id,
                "status": item.status.value,
                "actual_value": str(item.actual_value) if item.actual_value is not None else None,
                "reference_value": str(item.reference_value),
                "absolute_difference": str(item.absolute_difference) if item.absolute_difference is not None else None,
                "allowed_difference": str(item.allowed_difference),
            }
            for item in results
        ],
        "summary": {
            status.value: sum(1 for item in results if item.status == status)
            for status in ReconciliationStatus
        },
        "is_reference_validation_not_live_data": True,
    }
