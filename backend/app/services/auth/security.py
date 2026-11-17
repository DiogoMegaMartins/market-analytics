"""Password, access-token and opaque refresh-token primitives for the MVP."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from uuid import UUID

_ITERATIONS = 310_000


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt, expected = encoded.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), _unb64(salt), int(iterations))
        return hmac.compare_digest(actual, _unb64(expected))
    except (ValueError, TypeError):
        return False


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def create_access_token(user_id: UUID, secret: str, session_id: UUID | None = None,
                        expires_seconds: int = 900) -> str:
    now = int(time.time())
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    claims = {"sub": str(user_id), "iat": now, "exp": now + expires_seconds}
    if session_id is not None:
        claims["sid"] = str(session_id)
    payload = _b64(json.dumps(claims, separators=(",", ":")).encode())
    signing = f"{header}.{payload}"
    signature = _b64(hmac.new(secret.encode(), signing.encode(), hashlib.sha256).digest())
    return f"{signing}.{signature}"


def decode_access_token_claims(token: str, secret: str) -> tuple[UUID, UUID | None]:
    try:
        header, payload, signature = token.split(".")
        header_claims = json.loads(_unb64(header))
        if header_claims.get("alg") != "HS256" or header_claims.get("typ") != "JWT":
            raise ValueError()
        signing = f"{header}.{payload}"
        expected = _b64(hmac.new(secret.encode(), signing.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError()
        claims = json.loads(_unb64(payload))
        now = int(time.time())
        if claims.get("exp", 0) <= now or claims.get("iat", now + 1) > now + 60:
            raise ValueError()
        return UUID(claims["sub"]), UUID(claims["sid"]) if claims.get("sid") else None
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid or expired access token") from exc


def decode_access_token(token: str, secret: str) -> UUID:
    return decode_access_token_claims(token, secret)[0]


def refresh_replay_within_grace(consumed_at, now, grace_seconds: int = 10) -> bool:
    """Treat an immediate duplicate refresh as a concurrency race, not token theft.

    The stale token never issues credentials again. After the short grace period,
    reuse is treated as a replay and the session is revoked.
    """
    from datetime import timedelta

    if consumed_at is None:
        return False
    return now >= consumed_at and now - consumed_at <= timedelta(seconds=grace_seconds)
