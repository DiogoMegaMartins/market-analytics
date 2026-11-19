from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_company_access
from app.models.portfolio import Portfolio, PortfolioTransaction
from app.models.portfolio_benchmark import PortfolioBenchmark, PortfolioBenchmarkObservation
from app.models.portfolio_valuation import PortfolioValuationSnapshot
from app.platform.database.session import get_db_session
from app.services.portfolio.performance.benchmark import calculate_relative_performance
from app.services.portfolio.performance.benchmark_quality import build_benchmark_quality_report
from app.services.portfolio.performance.twr import calculate_time_weighted_return

router = APIRouter(tags=["portfolio"], dependencies=[Depends(require_company_access)])


class BenchmarkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=40, pattern=r"^[A-Z0-9._-]+$")
    name: str = Field(min_length=1, max_length=120)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    benchmark_type: Literal["TOTAL_RETURN_INDEX"] = "TOTAL_RETURN_INDEX"
    provider: str = Field(min_length=1, max_length=120)
    methodology: str = Field(min_length=1, max_length=240)
    source_reference: str | None = Field(default=None, max_length=240)

    @field_validator("name", "provider", "methodology")
    @classmethod
    def nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be blank")
        return value


class BenchmarkObservationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    observation_date: date
    index_level: Decimal
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    source: str = Field(min_length=1, max_length=120)
    source_reference: str | None = Field(default=None, max_length=240)
    methodology: str = Field(min_length=1, max_length=240)
    notes: str | None = None

    @field_validator("index_level")
    @classmethod
    def positive_finite(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value <= 0:
            raise ValueError("index_level must be finite and positive")
        return value

    @field_validator("source", "methodology")
    @classmethod
    def nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be blank")
        return value


def _benchmark_payload(item: PortfolioBenchmark) -> dict:
    return {
        "id": str(item.id), "company_id": str(item.company_id), "code": item.code,
        "name": item.name, "currency": item.currency, "benchmark_type": item.benchmark_type,
        "provider": item.provider, "methodology": item.methodology,
        "source_reference": item.source_reference, "is_active": item.is_active,
        "created_at": item.created_at.isoformat(),
    }


def _observation_payload(item: PortfolioBenchmarkObservation) -> dict:
    return {
        "id": str(item.id), "benchmark_id": str(item.benchmark_id), "company_id": str(item.company_id),
        "observation_date": item.observation_date.isoformat(), "index_level": str(item.index_level),
        "currency": item.currency, "source": item.source, "source_reference": item.source_reference,
        "methodology": item.methodology, "notes": item.notes, "recorded_at": item.recorded_at.isoformat(),
    }


async def _benchmark(company_id: UUID, benchmark_id: UUID, session: AsyncSession) -> PortfolioBenchmark:
    item = await session.scalar(select(PortfolioBenchmark).where(
        PortfolioBenchmark.id == benchmark_id, PortfolioBenchmark.company_id == company_id
    ))
    if item is None:
        raise HTTPException(status_code=404, detail="Benchmark not found")
    return item


@router.post("/portfolio/companies/{company_id}/benchmarks", status_code=201)
async def create_benchmark(
    company_id: UUID, data: BenchmarkCreate, request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    item = PortfolioBenchmark(
        company_id=company_id, code=data.code, name=data.name.strip(), currency=data.currency,
        benchmark_type=data.benchmark_type, provider=data.provider.strip(),
        methodology=data.methodology.strip(), source_reference=data.source_reference,
        created_by_user_id=request.state.authenticated_user.id, created_at=datetime.now(UTC),
    )
    session.add(item)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Benchmark code already exists for this company") from exc
    await session.refresh(item)
    return _benchmark_payload(item)


@router.get("/portfolio/companies/{company_id}/benchmarks")
async def list_benchmarks(
    company_id: UUID, session: AsyncSession = Depends(get_db_session),
) -> dict:
    items = list((await session.scalars(select(PortfolioBenchmark).where(
        PortfolioBenchmark.company_id == company_id
    ).order_by(PortfolioBenchmark.code))).all())
    return {"company_id": str(company_id), "benchmarks": [_benchmark_payload(item) for item in items]}


@router.post("/portfolio/companies/{company_id}/benchmarks/{benchmark_id}/observations", status_code=201)
async def create_benchmark_observation(
    company_id: UUID, benchmark_id: UUID, data: BenchmarkObservationCreate, request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    benchmark = await _benchmark(company_id, benchmark_id, session)
    if data.currency != benchmark.currency:
        raise HTTPException(status_code=422, detail="Observation currency must match benchmark currency")
    item = PortfolioBenchmarkObservation(
        benchmark_id=benchmark_id, company_id=company_id, observation_date=data.observation_date,
        index_level=data.index_level, currency=data.currency, source=data.source.strip(),
        source_reference=data.source_reference, methodology=data.methodology.strip(), notes=data.notes,
        recorded_at=datetime.now(UTC), created_by_user_id=request.state.authenticated_user.id,
    )
    session.add(item)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="An observation already exists for this benchmark and date") from exc
    await session.refresh(item)
    return _observation_payload(item)


@router.get("/portfolio/companies/{company_id}/benchmarks/{benchmark_id}/observations")
async def list_benchmark_observations(
    company_id: UUID, benchmark_id: UUID,
    start_date: date | None = Query(default=None), end_date: date | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    await _benchmark(company_id, benchmark_id, session)
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    query = select(PortfolioBenchmarkObservation).where(
        PortfolioBenchmarkObservation.company_id == company_id,
        PortfolioBenchmarkObservation.benchmark_id == benchmark_id,
    )
    if start_date:
        query = query.where(PortfolioBenchmarkObservation.observation_date >= start_date)
    if end_date:
        query = query.where(PortfolioBenchmarkObservation.observation_date <= end_date)
    items = list((await session.scalars(query.order_by(PortfolioBenchmarkObservation.observation_date))).all())
    return {"benchmark_id": str(benchmark_id), "observations": [_observation_payload(item) for item in items]}


@router.get("/portfolio/companies/{company_id}/portfolios/{portfolio_id}/performance/benchmark")
async def get_relative_performance(
    company_id: UUID, portfolio_id: UUID, benchmark_id: UUID,
    start_date: date = Query(...), end_date: date = Query(...),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    if end_date <= start_date:
        raise HTTPException(status_code=422, detail="end_date must be after start_date")
    portfolio = await session.scalar(select(Portfolio).where(
        Portfolio.id == portfolio_id, Portfolio.company_id == company_id
    ))
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    benchmark = await _benchmark(company_id, benchmark_id, session)
    if not benchmark.is_active:
        raise HTTPException(status_code=422, detail="Benchmark is inactive")
    if benchmark.currency != portfolio.base_currency:
        raise HTTPException(status_code=422, detail="Benchmark currency must match portfolio base currency; FX conversion is not supported")

    valuations = list((await session.scalars(select(PortfolioValuationSnapshot).where(
        PortfolioValuationSnapshot.portfolio_id == portfolio_id,
        PortfolioValuationSnapshot.company_id == company_id,
        PortfolioValuationSnapshot.valuation_date >= start_date,
        PortfolioValuationSnapshot.valuation_date <= end_date,
    ).order_by(PortfolioValuationSnapshot.valuation_date, PortfolioValuationSnapshot.recorded_at, PortfolioValuationSnapshot.id))).all())
    flows = list((await session.scalars(select(PortfolioTransaction).where(
        PortfolioTransaction.portfolio_id == portfolio_id,
        PortfolioTransaction.company_id == company_id,
        PortfolioTransaction.transaction_type.in_(("DEPOSIT", "WITHDRAWAL")),
        PortfolioTransaction.trade_date > start_date,
        PortfolioTransaction.trade_date <= end_date,
    ).order_by(PortfolioTransaction.trade_date, PortfolioTransaction.recorded_at, PortfolioTransaction.id))).all())
    observations = list((await session.scalars(select(PortfolioBenchmarkObservation).where(
        PortfolioBenchmarkObservation.company_id == company_id,
        PortfolioBenchmarkObservation.benchmark_id == benchmark_id,
        PortfolioBenchmarkObservation.observation_date.in_((start_date, end_date)),
    ))).all())
    levels = {item.observation_date: item.index_level for item in observations}
    if start_date not in levels or end_date not in levels:
        raise HTTPException(status_code=422, detail="Benchmark observations are required on both portfolio period boundary dates")

    try:
        twr = calculate_time_weighted_return(
            [{"valuation_date": item.valuation_date, "total_value": item.market_value + item.cash_value,
              "recorded_at": item.recorded_at, "id": item.id} for item in valuations],
            [{"flow_date": item.trade_date, "flow_type": item.transaction_type, "amount": item.gross_amount} for item in flows],
            start_date=start_date, end_date=end_date,
        )
        relative = calculate_relative_performance(
            portfolio_twr=twr["time_weighted_return"],
            benchmark_start_level=levels[start_date], benchmark_end_level=levels[end_date],
            start_date=start_date, end_date=end_date,
            portfolio_currency=portfolio.base_currency, benchmark_currency=benchmark.currency,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "company_id": str(company_id), "portfolio_id": str(portfolio_id),
        "benchmark": _benchmark_payload(benchmark),
        "benchmark_start_level": str(levels[start_date]),
        "benchmark_end_level": str(levels[end_date]),
        "benchmark_methodology": "TOTAL_RETURN_INDEX_LEVEL_RATIO",
        **relative,
        "portfolio_twr_method": twr["method"],
        "portfolio_coverage_status": twr["coverage_status"],
        "limitations": [
            "Benchmark observations must exist on both exact portfolio period boundary dates.",
            "Portfolio TWR uses the existing start-of-day external cash-flow convention.",
            "Benchmark observations are manually supplied and are not independently verified.",
            "No FX conversion, interpolation, or missing-observation estimation is performed.",
        ],
    }

@router.get("/portfolio/companies/{company_id}/benchmarks/{benchmark_id}/quality")
async def get_benchmark_quality(
    company_id: UUID,
    benchmark_id: UUID,
    max_gap_days: int = Query(default=7, ge=1, le=366),
    anomaly_threshold_percent: Decimal = Query(default=Decimal(20), gt=0),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return a read-only quality report for a benchmark observation series."""
    await _benchmark(company_id, benchmark_id, session)
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    query = select(PortfolioBenchmarkObservation).where(
        PortfolioBenchmarkObservation.company_id == company_id,
        PortfolioBenchmarkObservation.benchmark_id == benchmark_id,
    )
    if start_date:
        query = query.where(PortfolioBenchmarkObservation.observation_date >= start_date)
    if end_date:
        query = query.where(PortfolioBenchmarkObservation.observation_date <= end_date)
    observations = list((await session.scalars(
        query.order_by(PortfolioBenchmarkObservation.observation_date)
    )).all())
    try:
        report = build_benchmark_quality_report(
            observations,
            max_gap_days=max_gap_days,
            anomaly_threshold_percent=anomaly_threshold_percent,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"company_id": str(company_id), "benchmark_id": str(benchmark_id), **report}
