from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.business_quality import router as business_quality_router
from app.api.v1.endpoints.financial_data import router as financial_data_router
from app.api.v1.endpoints.identity import router as identity_router
from app.api.v1.endpoints.metrics import router as metrics_router
from app.api.v1.endpoints.portfolio import router as portfolio_router
from app.api.v1.endpoints.portfolio_performance import router as portfolio_performance_router
from app.api.v1.endpoints.portfolio_valuation import router as portfolio_valuation_router
from app.api.v1.endpoints.thesis import router as thesis_router
from app.api.v1.endpoints.valuation import router as valuation_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(identity_router)
api_router.include_router(financial_data_router)
api_router.include_router(metrics_router)
api_router.include_router(business_quality_router)
api_router.include_router(thesis_router)
api_router.include_router(valuation_router)
api_router.include_router(portfolio_router)
api_router.include_router(portfolio_valuation_router)
api_router.include_router(portfolio_performance_router)
