from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.auth import AuthSession, CompanyMembership, User
from app.models.business_quality import BusinessQualityAssessment
from app.models.business_quality_evidence import (
    BQDocumentSection,
    BQEvidenceCandidate,
    BQSourceDocument,
)
from app.models.thesis import InvestmentThesis
from app.platform.database.session import get_db_session
from app.services.auth.security import decode_access_token_claims, hash_refresh_token

bearer = HTTPBearer(auto_error=False)

async def get_current_user(request: Request,
                           credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                           session: AsyncSession = Depends(get_db_session)) -> User:
    cookie_token = request.cookies.get("ma_access")
    token = credentials.credentials if credentials is not None else cookie_token
    cookie_authenticated = credentials is None and cookie_token is not None
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required", headers={"WWW-Authenticate":"Bearer"})
    try:
        user_id, session_id = decode_access_token_claims(token, get_settings().secret_key.get_secret_value())
        if session_id is None:
            raise ValueError("Session-bound access token required")
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired access token", headers={"WWW-Authenticate":"Bearer"}) from exc
    user = await session.get(User, user_id)
    auth_session = await session.get(AuthSession, session_id)
    from datetime import UTC, datetime
    now = datetime.now(UTC)
    if user is None or not user.is_active or auth_session is None or auth_session.user_id != user_id or auth_session.revoked_at is not None or auth_session.expires_at <= now:
        raise HTTPException(status_code=401, detail="Session is revoked, expired or unavailable")
    if cookie_authenticated and request.method.upper() not in {"GET", "HEAD", "OPTIONS"}:
        csrf = request.headers.get("x-csrf-token", "")
        if not csrf or not __import__("hmac").compare_digest(hash_refresh_token(csrf), auth_session.csrf_token_hash):
            raise HTTPException(status_code=403, detail="CSRF token missing or invalid")
    request.state.auth_session = auth_session
    return user

def allowed_roles_for_company_write(path: str) -> set[str]:
    """Return the role gate for company-scoped POST operations.

    Action-specific review transitions are checked again by their endpoint handlers.
    """
    if "/evidence-candidates/" in path and path.endswith("/review"):
        return {"REVIEWER", "ADMIN"}
    if path.endswith("/review-events"):
        return {"ANALYST", "REVIEWER", "ADMIN"}
    return {"ANALYST", "ADMIN"}


async def require_company_access(request: Request, current_user: User = Depends(get_current_user),
                                 session: AsyncSession = Depends(get_db_session)) -> User:
    request.state.authenticated_user = current_user
    params = request.path_params
    company_id = params.get("company_id")
    resource_id = next((params.get(k) for k in ("assessment_id", "candidate_id", "document_id", "section_id", "asset_id", "thesis_id") if params.get(k)), None)
    if company_id is None and resource_id is not None:
        rid = UUID(str(resource_id))
        if "assessment_id" in params:
            obj = await session.get(BusinessQualityAssessment, rid)
            company_id = obj.company_id if obj else None
        elif "candidate_id" in params:
            obj = await session.get(BQEvidenceCandidate, rid)
            company_id = obj.company_id if obj else None
        elif "document_id" in params:
            obj = await session.get(BQSourceDocument, rid)
            company_id = obj.company_id if obj else None
        elif "section_id" in params:
            obj = await session.get(BQDocumentSection, rid)
            doc = await session.get(BQSourceDocument, obj.document_id) if obj else None
            company_id = doc.company_id if doc else None
        elif "asset_id" in params:
            from app.models.identity import Asset
            obj = await session.get(Asset, rid)
            company_id = obj.company_id if obj else None
        elif "thesis_id" in params:
            obj = await session.get(InvestmentThesis, rid)
            company_id = obj.company_id if obj else None
        if company_id is None:
            raise HTTPException(status_code=404, detail="Resource not found")
    if company_id is not None:
        membership = await session.scalar(select(CompanyMembership).where(
            CompanyMembership.user_id == current_user.id,
            CompanyMembership.company_id == UUID(str(company_id))))
        if membership is None:
            raise HTTPException(status_code=404, detail="Resource not found")
        method = request.method.upper()
        path = request.url.path
        request.state.company_role = membership.role
        if method == "POST" and membership.role not in allowed_roles_for_company_write(path):
            raise HTTPException(status_code=403, detail="Insufficient company role")
    return current_user
