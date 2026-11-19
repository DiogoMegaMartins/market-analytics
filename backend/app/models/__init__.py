"""SQLAlchemy model registry; import all models for Alembic metadata discovery."""

from app.models.auth import (
    AuthAuditEvent,
    AuthRefreshTokenHistory,
    AuthSession,
    CompanyMembership,
    LoginRateLimit,
    User,
)
from app.models.business_quality import BusinessQualityAssessment
from app.models.business_quality_evidence import (
    BQDocumentSection,
    BQEvidenceCandidate,
    BQSourceDocument,
)
from app.models.business_quality_evidence_audit import (
    BQAssessmentEvidenceLink,
    BQEvidenceReviewEvent,
)
from app.models.business_quality_review import BusinessQualityReviewEvent
from app.models.financial_data import (
    FinancialFact,
    FinancialFactLineage,
    FinancialMetricLineage,
    FinancialMetricResult,
    FinancialMetricRun,
    FinancialQualityFinding,
    NormalizedFinancialFact,
    SECProviderCache,
    SECRawCompanyFacts,
    ValuationRun,
)
from app.models.identity import Asset, AssetIdentifier, Company
from app.models.portfolio import Portfolio, PortfolioTransaction
from app.models.portfolio_benchmark import PortfolioBenchmark, PortfolioBenchmarkObservation
from app.models.portfolio_valuation import PortfolioValuationSnapshot
from app.models.thesis import InvestmentThesis, InvestmentThesisEvent, InvestmentThesisVersion
from app.models.thesis_alert import InvestmentThesisAlert, InvestmentThesisAlertEvent
from app.models.thesis_evidence import InvestmentThesisEvidenceLink
from app.platform.database.base import Base

__all__ = [
    "Asset",
    "AssetIdentifier",
    "AuthAuditEvent",
    "AuthRefreshTokenHistory",
    "AuthSession",
    "BQAssessmentEvidenceLink",
    "BQDocumentSection",
    "BQEvidenceCandidate",
    "BQEvidenceReviewEvent",
    "BQSourceDocument",
    "Base",
    "BusinessQualityAssessment",
    "BusinessQualityReviewEvent",
    "Company",
    "CompanyMembership",
    "FinancialFact",
    "FinancialFactLineage",
    "FinancialMetricLineage",
    "FinancialMetricResult",
    "FinancialMetricRun",
    "FinancialQualityFinding",
    "InvestmentThesis",
    "InvestmentThesisAlert",
    "InvestmentThesisAlertEvent",
    "InvestmentThesisEvent",
    "InvestmentThesisEvidenceLink",
    "InvestmentThesisVersion",
    "LoginRateLimit",
    "NormalizedFinancialFact",
    "Portfolio",
    "PortfolioBenchmark",
    "PortfolioBenchmarkObservation",
    "PortfolioTransaction",
    "PortfolioValuationSnapshot",
    "SECProviderCache",
    "SECRawCompanyFacts",
    "User",
    "ValuationRun",
]
