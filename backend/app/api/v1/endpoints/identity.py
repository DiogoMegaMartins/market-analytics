from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.models.auth import CompanyMembership, User
from app.models.identity import (
    Asset,
    AssetIdentifier,
    AssetType,
    Company,
    EntityStatus,
    IdentifierType,
    VerificationStatus,
)
from app.platform.database.session import get_db_session
from app.providers.sec.client import SECProviderError
from app.schemas.identity import (
    AssetCreate,
    AssetIdentifierRead,
    AssetRead,
    AssetSearchResult,
    CompanyCreate,
    CompanyRead,
)
from app.services.identity.sec_identity import SECTickerResolver

router = APIRouter(tags=["identity"], dependencies=[Depends(get_current_user)])


@router.post("/companies", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
async def create_company(
    payload: CompanyCreate, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)
) -> Company:
    company = Company(**payload.model_dump())
    session.add(company)
    await session.flush()
    session.add(CompanyMembership(user_id=current_user.id, company_id=company.id, role="ADMIN", created_at=datetime.now(UTC)))
    await session.commit()
    await session.refresh(company)
    return company


@router.post("/assets", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
async def create_asset(
    payload: AssetCreate, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)
) -> Asset:
    company = await session.get(Company, payload.company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    membership = await session.scalar(select(CompanyMembership).where(CompanyMembership.user_id == current_user.id, CompanyMembership.company_id == payload.company_id))
    if membership is None or membership.role not in {"ANALYST", "ADMIN"}:
        raise HTTPException(status_code=404, detail="Company not found")
    asset = Asset(**payload.model_dump())
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    return asset


@router.get("/assets/search", response_model=list[AssetSearchResult])
async def search_assets(
    q: str = Query(min_length=1, max_length=120),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[AssetSearchResult]:
    term = q.strip()
    if not term:
        return []
    accessible_company_ids = select(CompanyMembership.company_id).where(CompanyMembership.user_id == current_user.id)
    stmt = (
        select(Company)
        .outerjoin(Asset, Asset.company_id == Company.id)
        .outerjoin(AssetIdentifier, or_(
            AssetIdentifier.company_id == Company.id,
            AssetIdentifier.asset_id == Asset.id,
        ))
        .where(Company.id.in_(accessible_company_ids))
        .where(
            Company.legal_name.ilike(f"%{term}%")
            | Company.display_name.ilike(f"%{term}%")
            | Asset.name.ilike(f"%{term}%")
            | AssetIdentifier.value.ilike(f"{term}%")
        )
        .distinct()
        .limit(25)
    )
    companies = (await session.scalars(stmt)).all()
    results: list[AssetSearchResult] = []
    for company in companies:
        assets = (await session.scalars(select(Asset).where(Asset.company_id == company.id))).all()
        identifiers = (await session.scalars(select(AssetIdentifier).where(
            or_(AssetIdentifier.company_id == company.id,
                AssetIdentifier.asset_id.in_([asset.id for asset in assets] or [None]))
        ))).all()
        results.append(AssetSearchResult(
            company=CompanyRead.model_validate(company),
            assets=[AssetRead.model_validate(asset) for asset in assets],
            identifiers=[AssetIdentifierRead.model_validate(item) for item in identifiers],
        ))
    return results


@router.get("/sec/resolve/ticker")
async def resolve_sec_ticker(ticker: str = Query(min_length=1, max_length=20)) -> dict:
    try:
        candidates = await SECTickerResolver().resolve_ticker(ticker)
    except SECProviderError as exc:
        raise HTTPException(status_code=502, detail="SEC provider unavailable") from exc
    if not candidates:
        return {"status": "NOT_FOUND", "ticker": ticker.upper(), "candidates": []}
    if len(candidates) > 1:
        result_status = "AMBIGUOUS"
    else:
        result_status = "SINGLE_CANDIDATE"
    return {
        "status": result_status,
        "ticker": ticker.upper(),
        "candidates": [candidate.__dict__ for candidate in candidates],
    }


@router.get("/sec/verify-cik/{cik}")
async def verify_sec_cik(cik: str) -> dict:
    try:
        payload = await SECTickerResolver().verify_cik(cik)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SECProviderError as exc:
        raise HTTPException(status_code=502, detail="SEC provider unavailable") from exc
    return {
        "cik": str(payload.get("cik", "")).zfill(10),
        "name": payload.get("name"),
        "tickers": payload.get("tickers", []),
        "exchanges": payload.get("exchanges", []),
        "sic": payload.get("sic"),
        "sic_description": payload.get("sicDescription"),
        "fiscal_year_end": payload.get("fiscalYearEnd"),
    }


@router.post("/identity/register-sec", response_model=AssetSearchResult)
async def register_sec_ticker(
    ticker: str = Query(min_length=1, max_length=20),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AssetSearchResult:
    """Verify a unique SEC ticker candidate and register it idempotently."""
    resolver = SECTickerResolver()
    try:
        candidates = await resolver.resolve_ticker(ticker)
        if len(candidates) != 1:
            code = 404 if not candidates else 409
            detail = "Ticker not found by SEC" if not candidates else "Ticker is ambiguous; no registration performed"
            raise HTTPException(status_code=code, detail=detail)
        candidate = candidates[0]
        submission = await resolver.verify_cik(candidate.cik)
    except SECProviderError as exc:
        raise HTTPException(status_code=502, detail="SEC provider unavailable") from exc

    official_name = str(submission.get("name") or "").strip()
    raw_sic = submission.get("sic")
    sic_code = str(raw_sic).strip() if raw_sic is not None else None
    if sic_code is not None and (len(sic_code) != 4 or not sic_code.isascii() or not sic_code.isdigit()):
        sic_code = None
    sic_description = str(submission.get("sicDescription") or "").strip() or None
    if sic_description is not None:
        sic_description = sic_description[:256]
    sic_verified_at = datetime.now(UTC) if sic_code is not None else None
    official_tickers = {str(value).upper() for value in submission.get("tickers", [])}
    if not official_name or candidate.ticker not in official_tickers:
        raise HTTPException(status_code=409, detail="SEC identity verification did not confirm ticker")

    cik_result = await session.scalar(select(AssetIdentifier).where(
        AssetIdentifier.identifier_type == IdentifierType.CIK.value,
        AssetIdentifier.value == candidate.cik,
        AssetIdentifier.company_id.is_not(None),
    ))
    company = await session.get(Company, cik_result.company_id) if cik_result else None
    if company is not None:
        existing_membership = await session.scalar(select(CompanyMembership).where(CompanyMembership.user_id == current_user.id, CompanyMembership.company_id == company.id))
        if existing_membership is None or existing_membership.role not in {"ANALYST", "ADMIN"}:
            raise HTTPException(status_code=404, detail="Company not found")
    if company is None:
        company = Company(legal_name=official_name, display_name=official_name, sic_code=sic_code, sic_description=sic_description, sic_verified_at=sic_verified_at)
        session.add(company)
        await session.flush()
        from datetime import UTC, datetime
        session.add(CompanyMembership(user_id=current_user.id, company_id=company.id, role="ADMIN", created_at=datetime.now(UTC)))
        session.add(AssetIdentifier(
            company_id=company.id, identifier_type=IdentifierType.CIK.value,
            value=candidate.cik, verification_status=VerificationStatus.VERIFIED.value,
            source_name="SEC submissions",
            source_url=resolver.client.SUBMISSIONS_URL.format(cik=candidate.cik),
            valid_from=date.today(),
        ))
    elif company.legal_name.casefold() != official_name.casefold():
        raise HTTPException(status_code=409, detail="Existing CIK has a conflicting company name")
    if sic_code is not None:
        company.sic_code = sic_code
        company.sic_description = sic_description
        company.sic_verified_at = sic_verified_at

    existing_ticker = await session.scalar(select(AssetIdentifier).where(
        AssetIdentifier.identifier_type == IdentifierType.TICKER.value,
        AssetIdentifier.value == candidate.ticker,
        AssetIdentifier.asset_id.is_not(None),
    ))
    if existing_ticker is not None:
        existing_asset = await session.get(Asset, existing_ticker.asset_id)
        if existing_asset is None or existing_asset.company_id != company.id:
            await session.rollback()
            raise HTTPException(status_code=409, detail="Ticker is already assigned to another company")
        asset = existing_asset
    else:
        asset = Asset(company_id=company.id, asset_type=AssetType.COMMON_STOCK.value, name=official_name)
        session.add(asset)
        await session.flush()
        session.add(AssetIdentifier(
            asset_id=asset.id, identifier_type=IdentifierType.TICKER.value,
            value=candidate.ticker, exchange_name=candidate.exchange,
            verification_status=VerificationStatus.VERIFIED.value,
            source_name="SEC ticker exchange file", source_url=resolver.client.TICKER_EXCHANGE_URL,
            valid_from=date.today(),
        ))
    await session.commit()
    await session.refresh(company)
    await session.refresh(asset)
    identifiers = (await session.scalars(select(AssetIdentifier).where(
        or_(AssetIdentifier.company_id == company.id, AssetIdentifier.asset_id == asset.id)
    ))).all()
    return AssetSearchResult(
        company=CompanyRead.model_validate(company),
        assets=[AssetRead.model_validate(asset)],
        identifiers=[AssetIdentifierRead.model_validate(item) for item in identifiers],
    )
