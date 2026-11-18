from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_company_access
from app.models.identity import Asset, Company
from app.models.portfolio import Portfolio, PortfolioTransaction
from app.platform.database.session import get_db_session

router = APIRouter(tags=["portfolio"], dependencies=[Depends(require_company_access)])


class PortfolioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    base_currency: str = Field(pattern="^[A-Z]{3}$")


class PortfolioTransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transaction_type: Literal["BUY", "SELL", "DIVIDEND", "DEPOSIT", "WITHDRAWAL", "FEE", "TAX", "INTEREST"]
    trade_date: date
    settlement_date: date | None = None
    asset_id: UUID | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    gross_amount: Decimal
    currency: str | None = Field(default=None, pattern="^[A-Z]{3}$")
    fees: Decimal = Decimal("0")
    taxes: Decimal = Decimal("0")
    idempotency_key: str = Field(min_length=1, max_length=128)
    external_reference: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("quantity", "unit_price", "gross_amount", "fees", "taxes")
    @classmethod
    def finite_decimal(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not value.is_finite():
            raise ValueError("amounts and quantities must be finite")
        return value

    @model_validator(mode="after")
    def validate_transaction_shape(self):
        if self.gross_amount <= 0 or self.fees < 0 or self.taxes < 0:
            raise ValueError("gross_amount must be positive; fees and taxes cannot be negative")
        if self.settlement_date is not None and self.settlement_date < self.trade_date:
            raise ValueError("settlement_date cannot precede trade_date")
        if self.transaction_type in {"BUY", "SELL"}:
            if self.asset_id is None or self.quantity is None or self.unit_price is None:
                raise ValueError("BUY and SELL require asset_id, quantity and unit_price")
            if self.quantity <= 0 or self.unit_price <= 0:
                raise ValueError("quantity and unit_price must be positive")
            if self.gross_amount != self.quantity * self.unit_price:
                raise ValueError("gross_amount must equal quantity multiplied by unit_price")
        else:
            if self.quantity is not None or self.unit_price is not None:
                raise ValueError("quantity and unit_price are only valid for BUY and SELL")
            if self.transaction_type == "DIVIDEND" and self.asset_id is None:
                raise ValueError("DIVIDEND requires asset_id")
            if self.transaction_type in {"DEPOSIT", "WITHDRAWAL", "INTEREST"} and self.asset_id is not None:
                raise ValueError(f"{self.transaction_type} cannot reference an asset")
        return self


def _portfolio_payload(item: Portfolio) -> dict:
    return {
        "id": str(item.id), "company_id": str(item.company_id), "name": item.name,
        "base_currency": item.base_currency, "status": item.status,
        "created_by_user_id": str(item.created_by_user_id),
        "created_at": item.created_at.isoformat(), "updated_at": item.updated_at.isoformat(),
    }


def _transaction_payload(item: PortfolioTransaction, *, idempotent_replay: bool = False) -> dict:
    return {
        "id": str(item.id), "portfolio_id": str(item.portfolio_id),
        "company_id": str(item.company_id), "asset_id": str(item.asset_id) if item.asset_id else None,
        "transaction_type": item.transaction_type, "trade_date": item.trade_date.isoformat(),
        "settlement_date": item.settlement_date.isoformat() if item.settlement_date else None,
        "quantity": str(item.quantity) if item.quantity is not None else None,
        "unit_price": str(item.unit_price) if item.unit_price is not None else None,
        "gross_amount": str(item.gross_amount), "currency": item.currency,
        "fees": str(item.fees), "taxes": str(item.taxes),
        "idempotency_key": item.idempotency_key, "external_reference": item.external_reference,
        "notes": item.notes, "created_by_user_id": str(item.created_by_user_id),
        "recorded_at": item.recorded_at.isoformat(), "idempotent_replay": idempotent_replay,
    }


async def _portfolio_for_company(
    company_id: UUID, portfolio_id: UUID, session: AsyncSession
) -> Portfolio:
    portfolio = await session.scalar(select(Portfolio).where(
        Portfolio.id == portfolio_id, Portfolio.company_id == company_id
    ))
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


def _matches_existing(existing: PortfolioTransaction, payload: PortfolioTransactionCreate, currency: str) -> bool:
    return all((
        existing.transaction_type == payload.transaction_type,
        existing.trade_date == payload.trade_date,
        existing.settlement_date == payload.settlement_date,
        existing.asset_id == payload.asset_id,
        existing.quantity == payload.quantity,
        existing.unit_price == payload.unit_price,
        existing.gross_amount == payload.gross_amount,
        existing.currency == currency,
        existing.fees == payload.fees,
        existing.taxes == payload.taxes,
        existing.external_reference == payload.external_reference,
        existing.notes == payload.notes,
    ))


@router.post("/portfolio/companies/{company_id}/portfolios", status_code=201)
async def create_portfolio(
    company_id: UUID, payload: PortfolioCreate, request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    if await session.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    now = datetime.now(UTC)
    portfolio = Portfolio(
        company_id=company_id, name=payload.name.strip(), base_currency=payload.base_currency,
        status="ACTIVE", created_by_user_id=request.state.authenticated_user.id,
        created_at=now, updated_at=now,
    )
    session.add(portfolio)
    await session.commit()
    await session.refresh(portfolio)
    return _portfolio_payload(portfolio)


@router.get("/portfolio/companies/{company_id}/portfolios")
async def list_portfolios(
    company_id: UUID, limit: int = Query(default=50, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    if await session.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    records = list((await session.scalars(select(Portfolio).where(
        Portfolio.company_id == company_id
    ).order_by(Portfolio.created_at.desc(), Portfolio.id).limit(limit))).all())
    return {"company_id": str(company_id), "portfolios": [_portfolio_payload(item) for item in records]}


@router.get("/portfolio/companies/{company_id}/portfolios/{portfolio_id}")
async def get_portfolio(
    company_id: UUID, portfolio_id: UUID, session: AsyncSession = Depends(get_db_session),
) -> dict:
    return _portfolio_payload(await _portfolio_for_company(company_id, portfolio_id, session))


@router.post(
    "/portfolio/companies/{company_id}/portfolios/{portfolio_id}/transactions",
    status_code=201,
)
async def create_portfolio_transaction(
    company_id: UUID, portfolio_id: UUID, payload: PortfolioTransactionCreate,
    request: Request, session: AsyncSession = Depends(get_db_session),
) -> dict:
    portfolio = await _portfolio_for_company(company_id, portfolio_id, session)
    if portfolio.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Archived portfolios cannot accept transactions")
    currency = payload.currency or portfolio.base_currency
    if currency != portfolio.base_currency:
        raise HTTPException(status_code=422, detail="Transaction currency must match portfolio base currency; FX support is not yet enabled")
    if payload.asset_id is not None and await session.get(Asset, payload.asset_id) is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    existing = await session.scalar(select(PortfolioTransaction).where(
        PortfolioTransaction.portfolio_id == portfolio_id,
        PortfolioTransaction.idempotency_key == payload.idempotency_key,
    ))
    if existing is not None:
        if not _matches_existing(existing, payload, currency):
            raise HTTPException(status_code=409, detail="Idempotency key was already used with a different transaction")
        return _transaction_payload(existing, idempotent_replay=True)

    item = PortfolioTransaction(
        portfolio_id=portfolio_id, company_id=company_id, asset_id=payload.asset_id,
        transaction_type=payload.transaction_type, trade_date=payload.trade_date,
        settlement_date=payload.settlement_date, quantity=payload.quantity,
        unit_price=payload.unit_price, gross_amount=payload.gross_amount,
        currency=currency, fees=payload.fees, taxes=payload.taxes,
        idempotency_key=payload.idempotency_key, external_reference=payload.external_reference,
        notes=payload.notes, created_by_user_id=request.state.authenticated_user.id,
        recorded_at=datetime.now(UTC),
    )
    session.add(item)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await session.scalar(select(PortfolioTransaction).where(
            PortfolioTransaction.portfolio_id == portfolio_id,
            PortfolioTransaction.idempotency_key == payload.idempotency_key,
        ))
        if existing is not None and _matches_existing(existing, payload, currency):
            return _transaction_payload(existing, idempotent_replay=True)
        if existing is not None:
            raise HTTPException(status_code=409, detail="Idempotency key was already used with a different transaction")
        raise
    await session.refresh(item)
    return _transaction_payload(item)


@router.get(
    "/portfolio/companies/{company_id}/portfolios/{portfolio_id}/transactions"
)
async def list_portfolio_transactions(
    company_id: UUID, portfolio_id: UUID, limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0, le=100000),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    await _portfolio_for_company(company_id, portfolio_id, session)
    records = list((await session.scalars(select(PortfolioTransaction).where(
        PortfolioTransaction.portfolio_id == portfolio_id
    ).order_by(
        PortfolioTransaction.trade_date.desc(),
        PortfolioTransaction.recorded_at.desc(),
        PortfolioTransaction.id.desc(),
    ).limit(limit).offset(offset))).all())
    return {
        "portfolio_id": str(portfolio_id), "limit": limit, "offset": offset,
        "transactions": [_transaction_payload(item) for item in records],
    }
