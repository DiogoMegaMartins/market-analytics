from uuid import uuid4

import pytest

from app.services.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_round_trip_and_salt_uniqueness():
    first = hash_password("correct horse battery staple")
    second = hash_password("correct horse battery staple")
    assert first != second
    assert verify_password("correct horse battery staple", first)
    assert not verify_password("wrong password", first)


def test_password_minimum_length():
    with pytest.raises(ValueError):
        hash_password("short")


def test_signed_access_token_round_trip():
    user_id = uuid4()
    token = create_access_token(user_id, "unit-test-secret")
    assert decode_access_token(token, "unit-test-secret") == user_id


def test_access_token_rejects_wrong_secret_and_tampering():
    token = create_access_token(uuid4(), "unit-test-secret")
    with pytest.raises(ValueError):
        decode_access_token(token, "wrong-secret")
    head, body, signature = token.split(".")
    with pytest.raises(ValueError):
        decode_access_token(f"{head}.{body}x.{signature}", "unit-test-secret")


def test_access_token_rejects_non_hs256_header():
    import base64
    import json
    token = create_access_token(uuid4(), "unit-test-secret")
    _, body, _ = token.split(".")
    forged_header = base64.urlsafe_b64encode(json.dumps({"alg":"none","typ":"JWT"}).encode()).rstrip(b"=").decode()
    with pytest.raises(ValueError):
        decode_access_token(f"{forged_header}.{body}.invalid", "unit-test-secret")


def test_access_token_expiration_is_enforced():
    import hashlib
    import hmac
    import json
    import time
    from uuid import uuid4

    from app.services.auth.security import _b64
    header = _b64(json.dumps({"alg":"HS256","typ":"JWT"}).encode())
    payload = _b64(json.dumps({"sub":str(uuid4()),"iat":int(time.time())-10,"exp":int(time.time())-1}).encode())
    signing=f"{header}.{payload}"
    signature=_b64(hmac.new(b"secret",signing.encode(),hashlib.sha256).digest())
    with pytest.raises(ValueError):
        decode_access_token(f"{signing}.{signature}","secret")


def test_business_quality_api_rejects_missing_bearer_token():
    from fastapi.testclient import TestClient

    from app.main import app
    async def fake_session():
        yield object()
    from app.platform.database.session import get_db_session
    app.dependency_overrides[get_db_session] = fake_session
    try:
        response = TestClient(app).get("/api/v1/business-quality/criteria")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_access_token_is_bound_to_a_session():
    from app.services.auth.security import decode_access_token_claims
    user_id, session_id = uuid4(), uuid4()
    token = create_access_token(user_id, "unit-test-secret", session_id=session_id)
    assert decode_access_token_claims(token, "unit-test-secret") == (user_id, session_id)


def test_access_token_without_session_is_not_session_bound():
    from app.services.auth.security import decode_access_token_claims
    token = create_access_token(uuid4(), "unit-test-secret")
    assert decode_access_token_claims(token, "unit-test-secret")[1] is None


def test_refresh_token_hash_is_one_way_and_stable():
    from app.services.auth.security import create_refresh_token, hash_refresh_token
    token = create_refresh_token()
    assert len(token) >= 64
    assert hash_refresh_token(token) == hash_refresh_token(token)
    assert hash_refresh_token(token) != token
    assert hash_refresh_token(create_refresh_token()) != hash_refresh_token(token)


def test_identity_and_financial_routes_require_authentication():
    from fastapi.testclient import TestClient

    from app.main import app
    from app.platform.database.session import get_db_session

    async def fake_session():
        yield object()

    app.dependency_overrides[get_db_session] = fake_session
    try:
        client = TestClient(app)
        paths = [
            "/api/v1/assets/search?q=MSFT",
            "/api/v1/sec/resolve/ticker?ticker=MSFT",
            f"/api/v1/financial-data/companies/{uuid4()}/facts",
            f"/api/v1/metrics/companies/{uuid4()}/annual/2024/history",
        ]
        assert all(client.get(path).status_code == 401 for path in paths)
    finally:
        app.dependency_overrides.clear()


def test_business_quality_review_input_rejects_spoofed_actor_identity():
    from pydantic import ValidationError

    from app.api.v1.endpoints.business_quality import EvidenceReviewInput, ReviewActionInput
    with pytest.raises(ValidationError):
        EvidenceReviewInput(status="VERIFIED", reviewed_by="forged-user", review_comment="ok")
    with pytest.raises(ValidationError):
        ReviewActionInput(action="APPROVE", actor_id="forged-user", comment="ok")


def test_browser_auth_cookies_are_httponly_and_secure_outside_development():
    from fastapi import Response
    from pydantic import SecretStr

    from app.api.v1.endpoints.auth import _set_auth_cookies
    from app.core.config import Settings
    settings = Settings(app_env="production", app_debug=False, secret_key=SecretStr("s" * 48),
                        database_url="postgresql+asyncpg://u:p@localhost:5432/test",
                        cors_allowed_origins="https://research.example.com")
    response = Response()
    _set_auth_cookies(response, "access", "refresh", settings, "csrf")
    cookie_headers = response.headers.getlist("set-cookie")
    assert len(cookie_headers) == 2
    assert all("HttpOnly" in value and "Secure" in value and "SameSite=lax" in value for value in cookie_headers)
    assert "Path=/api/v1" in cookie_headers[0]
    assert "Path=/api/v1/auth" in cookie_headers[1]


def test_cookie_authenticated_writes_require_session_bound_csrf_token():
    import asyncio
    from datetime import UTC, datetime, timedelta
    from types import SimpleNamespace

    from fastapi import HTTPException
    from starlette.requests import Request

    from app.api.v1.dependencies import get_current_user
    from app.core.config import get_settings
    from app.services.auth.security import hash_refresh_token
    user_id, session_id = uuid4(), uuid4()
    csrf = "test-csrf-value"
    token = create_access_token(user_id, get_settings().secret_key.get_secret_value(), session_id=session_id)
    user = SimpleNamespace(id=user_id, is_active=True)
    auth_session = SimpleNamespace(id=session_id, user_id=user_id, revoked_at=None,
        expires_at=datetime.now(UTC) + timedelta(minutes=10), csrf_token_hash=hash_refresh_token(csrf))

    class FakeSession:
        async def get(self, model, ident):
            from app.models.auth import AuthSession, User
            return user if model is User else auth_session if model is AuthSession else None

    def make_request(headers):
        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": "POST", "scheme": "http", "path": "/api/v1/auth/logout", "raw_path": b"/api/v1/auth/logout",
            "query_string": b"", "root_path": "", "headers": headers,
            "client": ("127.0.0.1", 12345), "server": ("testserver", 80)}
        return Request(scope)

    async def run():
        cookie = (b"cookie", f"ma_access={token}".encode())
        with pytest.raises(HTTPException) as exc:
            await get_current_user(make_request([cookie]), None, FakeSession())
        assert exc.value.status_code == 403
        request = make_request([cookie, (b"x-csrf-token", csrf.encode())])
        assert await get_current_user(request, None, FakeSession()) is user
    asyncio.run(run())


def test_refresh_rotation_grace_distinguishes_concurrency_from_late_replay():
    from datetime import UTC, datetime, timedelta

    from app.services.auth.security import refresh_replay_within_grace

    consumed = datetime.now(UTC)
    assert refresh_replay_within_grace(consumed, consumed + timedelta(seconds=3), 10)
    assert refresh_replay_within_grace(consumed, consumed + timedelta(seconds=10), 10)
    assert not refresh_replay_within_grace(consumed, consumed + timedelta(seconds=11), 10)
    assert not refresh_replay_within_grace(None, consumed, 10)
    assert not refresh_replay_within_grace(consumed, consumed - timedelta(seconds=1), 10)


def test_session_management_routes_require_authenticated_user():
    # Inspect the public OpenAPI contract instead of FastAPI's internal route
    # objects: recent FastAPI releases keep included routers lazily in app.routes.
    from app.main import app

    paths = app.openapi()["paths"]
    expected = {
        "/api/v1/auth/sessions": {"get"},
        "/api/v1/auth/sessions/{session_id}": {"delete"},
    }
    for path, methods in expected.items():
        assert path in paths
        assert methods.issubset(paths[path])
        for method in methods:
            security = paths[path][method].get("security", [])
            assert any("HTTPBearer" in requirement for requirement in security), (
                f"{method.upper()} {path} must require bearer authentication"
            )
