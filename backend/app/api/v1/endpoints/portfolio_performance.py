from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_company_access
from app.models.portfolio import Portfolio, PortfolioTransaction
from app.models.portfolio_valuation import PortfolioValuationSnapshot
from app.platform.database.session import get_db_session
from app.services.portfolio.performance.twr import calculate_time_weighted_return

router = APIRouter(tags=["portfolio"], dependencies=[Depends(require_company_access)])


@router.get("/portfolio/companies/{company_id}/portfolios/{portfolio_id}/performance/twr")
async def get_portfolio_time_weighted_return(
    company_id: UUID,
    portfolio_id: UUID,
    start_date: date = Query(...),
    end_date: date = Query(...),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Calculate read-only daily-boundary TWR from dated NAV and external flows."""
    if end_date <= start_date:
        raise HTTPException(status_code=422, detail="end_date must be after start_date")
    portfolio = await session.scalar(select(Portfolio).where(
        Portfolio.id == portfolio_id, Portfolio.company_id == company_id
    ))
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    valuations = list((await session.scalars(select(PortfolioValuationSnapshot).where(
        PortfolioValuationSnapshot.portfolio_id == portfolio_id,
        PortfolioValuationSnapshot.company_id == company_id,
        PortfolioValuationSnapshot.valuation_date >= start_date,
        PortfolioValuationSnapshot.valuation_date <= end_date,
    ).order_by(
        PortfolioValuationSnapshot.valuation_date,
        PortfolioValuationSnapshot.recorded_at,
        PortfolioValuationSnapshot.id,
    ))).all())
    transactions = list((await session.scalars(select(PortfolioTransaction).where(
        PortfolioTransaction.portfolio_id == portfolio_id,
        PortfolioTransaction.company_id == company_id,
        PortfolioTransaction.transaction_type.in_(("DEPOSIT", "WITHDRAWAL")),
        PortfolioTransaction.trade_date > start_date,
        PortfolioTransaction.trade_date <= end_date,
    ).order_by(
        PortfolioTransaction.trade_date,
        PortfolioTransaction.recorded_at,
        PortfolioTransaction.id,
    ))).all())

    try:
        result = calculate_time_weighted_return(
            [{
                "valuation_date": item.valuation_date,
                "total_value": item.market_value + item.cash_value,
                "recorded_at": item.recorded_at,
                "id": item.id,
            } for item in valuations],
            [{
                "flow_date": item.trade_date,
                "flow_type": item.transaction_type,
                "amount": item.gross_amount,
            } for item in transactions],
            start_date=start_date,
            end_date=end_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "company_id": str(company_id),
        "portfolio_id": str(portfolio_id),
        "currency": portfolio.base_currency,
        **result,
    }
