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
from app.models.portfolio import Portfolio
from app.models.portfolio_valuation import PortfolioValuationSnapshot
from app.platform.database.session import get_db_session
from app.services.portfolio.performance.valuation_quality import build_portfolio_valuation_quality_report

router = APIRouter(tags=["portfolio"], dependencies=[Depends(require_company_access)])


class PortfolioValuationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    valuation_date: date
    market_value: Decimal
    cash_value: Decimal
    currency: str = Field(pattern="^[A-Z]{3}$")
    valuation_source: Literal["MANUAL", "BROKER_STATEMENT", "DATA_PROVIDER"] = "MANUAL"
    methodology: str = Field(min_length=1, max_length=160)
    source_reference: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=4000)
    idempotency_key: str = Field(min_length=1, max_length=128)

    @field_validator("market_value", "cash_value")
    @classmethod
    def finite_nonnegative(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value < 0:
            raise ValueError("valuation values must be finite and nonnegative")
        return value

    @field_validator("methodology")
    @classmethod
    def nonblank_methodology(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("methodology cannot be blank")
        return value


def _payload(item: PortfolioValuationSnapshot, *, replay: bool = False) -> dict:
    return {
        "id": str(item.id), "portfolio_id": str(item.portfolio_id), "company_id": str(item.company_id),
        "valuation_date": item.valuation_date.isoformat(), "market_value": str(item.market_value),
        "cash_value": str(item.cash_value), "total_value": str(item.market_value + item.cash_value),
        "currency": item.currency, "valuation_source": item.valuation_source,
        "methodology": item.methodology, "source_reference": item.source_reference,
        "notes": item.notes, "idempotency_key": item.idempotency_key,
        "created_by_user_id": str(item.created_by_user_id), "recorded_at": item.recorded_at.isoformat(),
        "idempotent_replay": replay,
    }


async def _portfolio(company_id: UUID, portfolio_id: UUID, session: AsyncSession) -> Portfolio:
    item = await session.scalar(select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.company_id == company_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return item


def _same(item: PortfolioValuationSnapshot, data: PortfolioValuationCreate, currency: str) -> bool:
    return all((
        item.valuation_date == data.valuation_date, item.market_value == data.market_value,
        item.cash_value == data.cash_value, item.currency == currency,
        item.valuation_source == data.valuation_source, item.methodology == data.methodology,
        item.source_reference == data.source_reference, item.notes == data.notes,
    ))


@router.post("/portfolio/companies/{company_id}/portfolios/{portfolio_id}/valuations", status_code=201)
async def create_portfolio_valuation(
    company_id: UUID, portfolio_id: UUID, data: PortfolioValuationCreate, request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    portfolio = await _portfolio(company_id, portfolio_id, session)
    if data.currency != portfolio.base_currency:
        raise HTTPException(status_code=422, detail="Valuation currency must match portfolio base currency; FX support is not enabled")
    existing = await session.scalar(select(PortfolioValuationSnapshot).where(
        PortfolioValuationSnapshot.portfolio_id == portfolio_id,
        PortfolioValuationSnapshot.idempotency_key == data.idempotency_key,
    ))
    if existing is not None:
        if not _same(existing, data, portfolio.base_currency):
            raise HTTPException(status_code=409, detail="Idempotency key was already used with a different valuation")
        return _payload(existing, replay=True)
    item = PortfolioValuationSnapshot(
        portfolio_id=portfolio_id, company_id=company_id, valuation_date=data.valuation_date,
        market_value=data.market_value, cash_value=data.cash_value, currency=data.currency,
        valuation_source=data.valuation_source, methodology=data.methodology,
        source_reference=data.source_reference, notes=data.notes, idempotency_key=data.idempotency_key,
        created_by_user_id=request.state.authenticated_user.id, recorded_at=datetime.now(UTC),
    )
    session.add(item)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await session.scalar(select(PortfolioValuationSnapshot).where(
            PortfolioValuationSnapshot.portfolio_id == portfolio_id,
            PortfolioValuationSnapshot.idempotency_key == data.idempotency_key,
        ))
        if existing is not None and _same(existing, data, portfolio.base_currency):
            return _payload(existing, replay=True)
        if existing is not None:
            raise HTTPException(status_code=409, detail="Idempotency key was already used with a different valuation")
        raise
    await session.refresh(item)
    return _payload(item)


@router.get("/portfolio/companies/{company_id}/portfolios/{portfolio_id}/valuations")
async def list_portfolio_valuations(
    company_id: UUID, portfolio_id: UUID,
    limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0, le=100000),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    await _portfolio(company_id, portfolio_id, session)
    items = list((await session.scalars(select(PortfolioValuationSnapshot).where(
        PortfolioValuationSnapshot.portfolio_id == portfolio_id
    ).order_by(
        PortfolioValuationSnapshot.valuation_date.desc(),
        PortfolioValuationSnapshot.recorded_at.desc(),
        PortfolioValuationSnapshot.id.desc(),
    ).limit(limit).offset(offset))).all())
    return {"portfolio_id": str(portfolio_id), "limit": limit, "offset": offset, "valuations": [_payload(item) for item in items]}



@router.get("/portfolio/companies/{company_id}/portfolios/{portfolio_id}/valuations/quality")
async def get_portfolio_valuation_quality(
    company_id: UUID,
    portfolio_id: UUID,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    max_gap_days: int = Query(default=7, ge=1, le=366),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return read-only valuation coverage and canonical-selection diagnostics."""
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    portfolio = await _portfolio(company_id, portfolio_id, session)
    statement = select(PortfolioValuationSnapshot).where(
        PortfolioValuationSnapshot.portfolio_id == portfolio_id,
        PortfolioValuationSnapshot.company_id == company_id,
    )
    if start_date is not None:
        statement = statement.where(PortfolioValuationSnapshot.valuation_date >= start_date)
    if end_date is not None:
        statement = statement.where(PortfolioValuationSnapshot.valuation_date <= end_date)
    snapshots = list((await session.scalars(statement.order_by(
        PortfolioValuationSnapshot.valuation_date,
        PortfolioValuationSnapshot.recorded_at,
        PortfolioValuationSnapshot.id,
    ))).all())
    return {"company_id": str(company_id), "portfolio_id": str(portfolio_id),
            "currency": portfolio.base_currency,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            **build_portfolio_valuation_quality_report(snapshots, max_gap_days=max_gap_days)}
