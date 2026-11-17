from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.core.config import get_settings
from app.models.auth import (
    AuthAuditEvent,
    AuthRefreshTokenHistory,
    AuthSession,
    CompanyMembership,
    LoginRateLimit,
    User,
)
from app.models.identity import Company
from app.platform.database.session import get_db_session
from app.services.auth.security import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    refresh_replay_within_grace,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
ACCESS_TTL_SECONDS = 900
REFRESH_TTL_DAYS = 30
LOGIN_WINDOW_SECONDS = 900
LOGIN_MAX_ATTEMPTS = 8
LOGIN_BLOCK_SECONDS = 900
REFRESH_REPLAY_GRACE_SECONDS = 10

class LoginInput(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)

class RefreshInput(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=32, max_length=256)

class UserProfile(BaseModel):
    id: str
    email: str
    display_name: str
    memberships: list[dict]

class MembershipInput(BaseModel):
    role: str = Field(pattern="^(ANALYST|REVIEWER|ADMIN)$")


def _audit(session: AsyncSession, user_id: UUID | None, event_type: str, success: bool, request: Request | None, details: str | None = None) -> None:
    session.add(AuthAuditEvent(user_id=user_id, event_type=event_type, success=success,
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500] or None if request else None,
        details=details, created_at=datetime.now(UTC)))

async def _enforce_login_limit(session: AsyncSession, key_hash: str, now: datetime, max_attempts: int = LOGIN_MAX_ATTEMPTS) -> None:
    from sqlalchemy import case
    reset = LoginRateLimit.window_started_at < now - timedelta(seconds=LOGIN_WINDOW_SECONDS)
    stmt = pg_insert(LoginRateLimit).values(key_hash=key_hash, window_started_at=now, attempts=1)
    stmt = stmt.on_conflict_do_update(index_elements=[LoginRateLimit.key_hash], set_={
        "attempts": case((reset, 1), else_=LoginRateLimit.attempts + 1),
        "window_started_at": case((reset, now), else_=LoginRateLimit.window_started_at),
        "blocked_until": case((reset, None), (LoginRateLimit.attempts + 1 >= max_attempts,
            now + timedelta(seconds=LOGIN_BLOCK_SECONDS)), else_=LoginRateLimit.blocked_until),
    })
    await session.execute(stmt)
    row = await session.scalar(select(LoginRateLimit).where(LoginRateLimit.key_hash == key_hash))
    if row and row.blocked_until and row.blocked_until > now:
        await session.commit()
        raise HTTPException(status_code=429, detail="Too many login attempts; try again later",
                            headers={"Retry-After": str(LOGIN_BLOCK_SECONDS)})

def _set_auth_cookies(response: Response, access_token: str, refresh_token: str, settings, csrf_token: str) -> None:
    secure = settings.app_env in {"staging", "production"}
    response.set_cookie("ma_access", access_token, max_age=ACCESS_TTL_SECONDS, httponly=True, secure=secure,
                        samesite="lax", path="/api/v1")
    response.set_cookie("ma_refresh", refresh_token, max_age=REFRESH_TTL_DAYS * 86400, httponly=True, secure=secure,
                        samesite="lax", path="/api/v1/auth")

async def _issue_session(session: AsyncSession, user: User, request: Request) -> dict:
    now = datetime.now(UTC)
    refresh = create_refresh_token()
    csrf = secrets.token_urlsafe(32)
    record = AuthSession(user_id=user.id, refresh_token_hash=hash_refresh_token(refresh), csrf_token_hash=hash_refresh_token(csrf),
        created_at=now, expires_at=now + timedelta(days=REFRESH_TTL_DAYS),
        user_agent=request.headers.get("user-agent", "")[:500] or None,
        ip_address=request.client.host if request.client else None)
    session.add(record)
    await session.flush()
    session.add(AuthRefreshTokenHistory(session_id=record.id, token_hash=record.refresh_token_hash, issued_at=now))
    token = create_access_token(user.id, get_settings().secret_key.get_secret_value(),
                                session_id=record.id, expires_seconds=ACCESS_TTL_SECONDS)
    return {"access_token": token, "refresh_token": refresh, "csrf_token": csrf, "token_type": "cookie",
            "expires_in": ACCESS_TTL_SECONDS, "refresh_expires_in": REFRESH_TTL_DAYS * 86400}

@router.post("/token")
async def login(payload: LoginInput, request: Request, response: Response, session: AsyncSession = Depends(get_db_session)) -> dict:
    now = datetime.now(UTC)
    email = payload.email.strip().lower()
    ip = request.client.host if request.client else "unknown"
    key_hash = hashlib.sha256(f"{email}|{ip}".encode()).hexdigest()
    await _enforce_login_limit(session, key_hash, now)
    ip_key_hash = hashlib.sha256(f"ip|{ip}".encode()).hexdigest()
    await _enforce_login_limit(session, ip_key_hash, now, max_attempts=40)
    user = await session.scalar(select(User).where(User.email == email))
    valid = bool(user and user.is_active and verify_password(payload.password, user.password_hash))
    _audit(session, user.id if user and valid else None, "LOGIN", valid, request,
           None if valid else "Invalid credentials")
    if not valid:
        await session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials",
                            headers={"WWW-Authenticate": "Bearer"})
    await session.execute(delete(LoginRateLimit).where(LoginRateLimit.key_hash.in_([key_hash, ip_key_hash])))
    result = await _issue_session(session, user, request)
    _set_auth_cookies(response, result["access_token"], result["refresh_token"], get_settings(), result["csrf_token"])
    public_result = {k: v for k, v in result.items() if k not in {"access_token", "refresh_token"}}
    await session.commit()
    return public_result

@router.post("/refresh")
async def refresh_access_token(payload: RefreshInput, request: Request, response: Response,
                               session: AsyncSession = Depends(get_db_session)) -> dict:
    now = datetime.now(UTC)
    cookie_refresh = request.cookies.get("ma_refresh")
    raw_refresh = payload.refresh_token or cookie_refresh
    if not raw_refresh:
        raise HTTPException(status_code=401, detail="Refresh token required")
    token_hash = hash_refresh_token(raw_refresh)
    history = await session.scalar(select(AuthRefreshTokenHistory).where(
        AuthRefreshTokenHistory.token_hash == token_hash).with_for_update())
    auth_session = await session.get(AuthSession, history.session_id, with_for_update=True) if history else None
    if history is not None and history.consumed_at is not None and auth_session is not None:
        if refresh_replay_within_grace(history.consumed_at, now, REFRESH_REPLAY_GRACE_SECONDS):
            # Another tab/request already rotated this token. Do not revoke the
            # session: this request receives no cookies and cannot reuse the token.
            _audit(session, auth_session.user_id, "REFRESH_DUPLICATE_GRACE", False, request,
                   "Concurrent refresh duplicate within grace window")
            await session.commit()
            raise HTTPException(status_code=409, detail="Refresh already completed; retry using the updated session cookie",
                                headers={"Retry-After": "1"})
        auth_session.revoked_at = now
        _audit(session, auth_session.user_id, "REFRESH_REUSE_DETECTED", False, request, "Previously consumed refresh token replayed outside grace window")
        await session.commit()
        raise HTTPException(status_code=401, detail="Refresh token reuse detected; session revoked")
    if history is None or auth_session is None or auth_session.revoked_at is not None or auth_session.expires_at <= now:
        _audit(session, auth_session.user_id if auth_session else None, "REFRESH", False, request, "Invalid or expired refresh token")
        await session.commit()
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    if cookie_refresh and not payload.refresh_token:
        csrf = request.headers.get("x-csrf-token", "")
        if not csrf or not secrets.compare_digest(hash_refresh_token(csrf), auth_session.csrf_token_hash):
            raise HTTPException(status_code=403, detail="CSRF token missing or invalid")
    user = await session.get(User, auth_session.user_id)
    if user is None or not user.is_active:
        auth_session.revoked_at = now
        _audit(session, auth_session.user_id, "REFRESH", False, request, "Inactive user")
        await session.commit()
        raise HTTPException(status_code=401, detail="User is inactive")
    history.consumed_at = now
    new_refresh = create_refresh_token()
    new_hash = hash_refresh_token(new_refresh)
    auth_session.refresh_token_hash = new_hash
    session.add(AuthRefreshTokenHistory(session_id=auth_session.id, token_hash=new_hash, issued_at=now))
    auth_session.last_used_at = now
    access_token = create_access_token(user.id, get_settings().secret_key.get_secret_value(),
              session_id=auth_session.id, expires_seconds=ACCESS_TTL_SECONDS)
    csrf_token = secrets.token_urlsafe(32)
    auth_session.csrf_token_hash = hash_refresh_token(csrf_token)
    _set_auth_cookies(response, access_token, new_refresh, get_settings(), csrf_token)
    result = {"csrf_token": csrf_token, "token_type": "cookie", "expires_in": ACCESS_TTL_SECONDS,
              "refresh_expires_in": int((auth_session.expires_at - now).total_seconds())}
    _audit(session, user.id, "REFRESH", True, request)
    await session.commit()
    return result

@router.post("/logout", status_code=204, response_class=Response, response_model=None)
async def logout(request: Request, response: Response, current_user: User = Depends(get_current_user),
                 session: AsyncSession = Depends(get_db_session)) -> None:
    now = datetime.now(UTC)
    auth_session = request.state.auth_session
    auth_session.revoked_at = now
    _audit(session, current_user.id, "LOGOUT", True, request)
    response.delete_cookie("ma_access", path="/api/v1")
    response.delete_cookie("ma_refresh", path="/api/v1/auth")
    await session.commit()

@router.post("/logout-all", status_code=204, response_class=Response, response_model=None)
async def logout_all(request: Request, response: Response, current_user: User = Depends(get_current_user),
                     session: AsyncSession = Depends(get_db_session)) -> None:
    now = datetime.now(UTC)
    rows = (await session.scalars(select(AuthSession).where(AuthSession.user_id == current_user.id,
        AuthSession.revoked_at.is_(None)))).all()
    for row in rows:
        row.revoked_at = now
    _audit(session, current_user.id, "LOGOUT_ALL", True, request)
    response.delete_cookie("ma_access", path="/api/v1")
    response.delete_cookie("ma_refresh", path="/api/v1/auth")
    await session.commit()

@router.get("/sessions")
async def list_sessions(request: Request, current_user: User = Depends(get_current_user),
                        session: AsyncSession = Depends(get_db_session)) -> dict:
    now = datetime.now(UTC)
    rows = list((await session.scalars(select(AuthSession).where(
        AuthSession.user_id == current_user.id
    ).order_by(AuthSession.created_at.desc()))).all())
    current_session_id = request.state.auth_session.id
    return {"sessions": [{
        "id": str(row.id), "created_at": row.created_at.isoformat(),
        "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
        "expires_at": row.expires_at.isoformat(), "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None,
        "is_current": row.id == current_session_id, "is_active": row.revoked_at is None and row.expires_at > now,
        "user_agent": row.user_agent, "ip_address": row.ip_address,
    } for row in rows]}


@router.delete("/sessions/{session_id}", status_code=204, response_class=Response, response_model=None)
async def revoke_session(session_id: UUID, request: Request, response: Response,
                         current_user: User = Depends(get_current_user),
                         session: AsyncSession = Depends(get_db_session)) -> None:
    row = await session.scalar(select(AuthSession).where(
        AuthSession.id == session_id, AuthSession.user_id == current_user.id
    ).with_for_update())
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)
        _audit(session, current_user.id, "SESSION_REVOKED", True, request, f"session_id={session_id}")
    if request.state.auth_session.id == row.id:
        response.delete_cookie("ma_access", path="/api/v1")
        response.delete_cookie("ma_refresh", path="/api/v1/auth")
    await session.commit()


@router.get("/me", response_model=UserProfile)
async def me(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)) -> UserProfile:
    rows = (await session.execute(select(CompanyMembership.company_id, CompanyMembership.role)
                                  .where(CompanyMembership.user_id == current_user.id))).all()
    return UserProfile(id=str(current_user.id), email=current_user.email, display_name=current_user.display_name,
        memberships=[{"company_id": str(r.company_id), "role": r.role} for r in rows])

@router.get("/companies/{company_id}/members")
async def list_company_members(company_id: UUID, current_user: User = Depends(get_current_user),
                               session: AsyncSession = Depends(get_db_session)) -> dict:
    admin = await session.scalar(select(CompanyMembership).where(CompanyMembership.user_id == current_user.id,
        CompanyMembership.company_id == company_id, CompanyMembership.role == "ADMIN"))
    if admin is None:
        raise HTTPException(status_code=404, detail="Company not found")
    rows = (await session.execute(select(User.id, User.email, User.display_name, User.is_active,
        CompanyMembership.role).join(CompanyMembership, CompanyMembership.user_id == User.id)
        .where(CompanyMembership.company_id == company_id).order_by(User.email))).all()
    return {"company_id": str(company_id), "members": [{"user_id": str(r.id), "email": r.email,
        "display_name": r.display_name, "is_active": r.is_active, "role": r.role} for r in rows]}

@router.put("/companies/{company_id}/members/{user_id}")
async def set_company_member_role(company_id: UUID, user_id: UUID, payload: MembershipInput, request: Request,
                                  current_user: User = Depends(get_current_user),
                                  session: AsyncSession = Depends(get_db_session)) -> dict:
    # Lock the company row first so concurrent role changes cannot remove the
    # final administrator through separate transactions.
    company = await session.scalar(select(Company).where(Company.id == company_id).with_for_update())
    admin = await session.scalar(select(CompanyMembership).where(CompanyMembership.user_id == current_user.id,
        CompanyMembership.company_id == company_id, CompanyMembership.role == "ADMIN").with_for_update())
    target = await session.get(User, user_id)
    if admin is None or target is None or company is None:
        raise HTTPException(status_code=404, detail="Company or user not found")
    membership = await session.scalar(select(CompanyMembership).where(CompanyMembership.user_id == user_id,
        CompanyMembership.company_id == company_id).with_for_update())
    now = datetime.now(UTC)
    previous_role = membership.role if membership else None
    if membership is None:
        membership = CompanyMembership(user_id=user_id, company_id=company_id, role=payload.role, created_at=now)
        session.add(membership)
    else:
        if previous_role == "ADMIN" and payload.role != "ADMIN":
            admin_count = await session.scalar(select(func.count()).select_from(CompanyMembership).where(
                CompanyMembership.company_id == company_id, CompanyMembership.role == "ADMIN"))
            if (admin_count or 0) <= 1:
                raise HTTPException(status_code=409, detail="A company must retain at least one administrator")
        membership.role = payload.role
    _audit(session, current_user.id, "MEMBERSHIP_ROLE_CHANGED", True, request,
           f"company={company_id};user={user_id};from={previous_role or 'NONE'};to={payload.role}")
    await session.commit()
    return {"company_id": str(company_id), "user_id": str(user_id), "role": membership.role}
