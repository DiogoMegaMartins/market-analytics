"""Real PostgreSQL checks for company-level authorization boundaries."""
from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.requests import Request

from app.api.v1.dependencies import allowed_roles_for_company_write, require_company_access
from app.models.auth import CompanyMembership, User
from app.models.business_quality_evidence import BQEvidenceCandidate, BQSourceDocument
from app.models.identity import Company

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL is not configured")


def _request(path: str, path_params: dict[str, str], method: str = "POST") -> Request:
    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
        "query_string": b"", "headers": [], "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345), "path_params": path_params,
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_company_membership_allows_own_tenant_and_hides_other_tenant() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            own_company = Company(legal_name=f"Own tenant {uuid4()}")
            other_company = Company(legal_name=f"Other tenant {uuid4()}")
            user = User(email=f"tenant-{uuid4()}@example.test", password_hash="not-used", display_name="Tenant Analyst")
            session.add_all([own_company, other_company, user])
            await session.flush()
            session.add(CompanyMembership(
                user_id=user.id, company_id=own_company.id, role="ANALYST",
                created_at=datetime.now(UTC),
            ))
            await session.flush()
            other_document = BQSourceDocument(
                company_id=other_company.id, accession_number="0000000000-26-000001",
                form_type="10-K", filed_at=datetime.now(UTC),
                source_url="https://www.sec.gov/Archives/edgar/data/1/example.htm",
                content_type="text/html", document_hash="a" * 64,
                original_content=b"<html>private tenant filing</html>",
                extraction_version="test-v1", created_at=datetime.now(UTC),
            )
            session.add(other_document)
            await session.flush()
            private_candidate = BQEvidenceCandidate(
                company_id=other_company.id, document_id=other_document.id,
                criterion_key="BUSINESS_MODEL_CLARITY", passage="private passage",
                rationale="test", status="CANDIDATE", source_locator="section:1",
                evidence_hash="b" * 64, created_by=str(uuid4()),
                created_at=datetime.now(UTC),
            )
            session.add(private_candidate)
            await session.flush()

            own_request = _request(
                f"/api/v1/business-quality/companies/{own_company.id}/assessments",
                {"company_id": str(own_company.id)},
            )
            await require_company_access(own_request, user, session)
            assert own_request.state.company_role == "ANALYST"

            other_request = _request(
                f"/api/v1/business-quality/companies/{other_company.id}/assessments",
                {"company_id": str(other_company.id)},
            )
            with pytest.raises(HTTPException) as error:
                await require_company_access(other_request, user, session)
            assert error.value.status_code == 404

            private_resource_request = _request(
                f"/api/v1/business-quality/evidence-candidates/{private_candidate.id}",
                {"candidate_id": str(private_candidate.id)}, method="GET",
            )
            with pytest.raises(HTTPException) as resource_error:
                await require_company_access(private_resource_request, user, session)
            assert resource_error.value.status_code == 404
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_reviewer_cannot_create_assessment_but_can_review_evidence() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            company = Company(legal_name=f"Review tenant {uuid4()}")
            user = User(email=f"reviewer-{uuid4()}@example.test", password_hash="not-used", display_name="Reviewer")
            session.add_all([company, user])
            await session.flush()
            session.add(CompanyMembership(
                user_id=user.id, company_id=company.id, role="REVIEWER",
                created_at=datetime.now(UTC),
            ))

            create_request = _request(
                f"/api/v1/business-quality/companies/{company.id}/assessments",
                {"company_id": str(company.id)},
            )
            with pytest.raises(HTTPException) as error:
                await require_company_access(create_request, user, session)
            assert error.value.status_code == 403

            review_request = _request(
                "/api/v1/business-quality/evidence-candidates/00000000-0000-0000-0000-000000000001/review",
                {"company_id": str(company.id), "candidate_id": "00000000-0000-0000-0000-000000000001"},
            )
            await require_company_access(review_request, user, session)
            assert review_request.state.company_role == "REVIEWER"
    finally:
        await engine.dispose()


def test_review_and_write_role_policies_are_explicit() -> None:
    assert allowed_roles_for_company_write("/business-quality/assessments/x/review-events") == {"ANALYST", "REVIEWER", "ADMIN"}
    assert allowed_roles_for_company_write("/business-quality/evidence-candidates/x/review") == {"REVIEWER", "ADMIN"}
    assert allowed_roles_for_company_write("/business-quality/companies/x/assessments") == {"ANALYST", "ADMIN"}
