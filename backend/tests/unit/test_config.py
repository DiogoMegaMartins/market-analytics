import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_requires_strong_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", secret_key="development-only-change-me")


def test_production_rejects_debug_mode() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            app_debug=True,
            secret_key="a-unique-secret-with-at-least-32-characters",
            database_url="postgresql+asyncpg://u:p@localhost:5432/test",
        )


def test_database_url_must_use_async_postgres_driver() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite:///local.db")


def test_production_requires_explicit_database_url(monkeypatch) -> None:
    # Ignore developer .env / process environment so this test verifies the
    # explicit-constructor contract rather than the machine's local settings.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL_UNPOOLED", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production", secret_key="s" * 48,
                 cors_allowed_origins="https://app.example.com")


def test_remote_production_database_requires_tls() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", secret_key="s" * 48,
                 database_url="postgresql+asyncpg://u:p@neon.example/db",
                 cors_allowed_origins="https://app.example.com")


def test_neon_connection_string_is_normalized_and_tls_is_retained() -> None:
    settings = Settings(app_env="production", secret_key="s" * 48,
        database_url="postgresql://u:p@neon.example/db?sslmode=require",
        cors_allowed_origins="https://app.example.com")
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert "ssl=require" in settings.database_url


def test_sec_retry_settings_must_be_valid() -> None:
    with pytest.raises(ValidationError):
        Settings(sec_max_attempts=0)
    with pytest.raises(ValidationError):
        Settings(sec_retry_base_seconds=5, sec_retry_max_seconds=2)


def test_sec_cache_ttl_cannot_be_negative() -> None:
    with pytest.raises(ValidationError):
        Settings(sec_company_facts_cache_ttl_seconds=-1)


def test_cors_origins_are_configurable():
    settings = Settings(cors_allowed_origins="http://localhost:3000,https://research.example.com")
    assert settings.cors_allowed_origins.split(",") == [
        "http://localhost:3000", "https://research.example.com"
    ]


def test_production_rejects_wildcard_cors_origin() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            secret_key="a-unique-secret-with-at-least-32-characters",
            database_url="postgresql+asyncpg://u:p@localhost:5432/test",
            cors_allowed_origins="*",
        )


def test_production_requires_https_cors_origins() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env="staging",
            secret_key="a-unique-secret-with-at-least-32-characters",
            database_url="postgresql+asyncpg://u:p@localhost:5432/test",
            cors_allowed_origins="http://research.example.com",
        )


def test_production_accepts_explicit_https_origins() -> None:
    settings = Settings(
        app_env="production",
        secret_key="a-unique-secret-with-at-least-32-characters",
        database_url="postgresql+asyncpg://u:p@localhost:5432/test",
        cors_allowed_origins="https://research.example.com,https://app.example.com",
    )
    assert "https://research.example.com" in settings.cors_allowed_origins


def test_production_rejects_wildcard_subdomain_cors_origin() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            secret_key="a-unique-secret-with-at-least-32-characters",
            database_url="postgresql+asyncpg://u:p@localhost:5432/test",
            cors_allowed_origins="https://*.example.com",
        )


def test_production_rejects_short_metrics_token() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            secret_key="a-unique-secret-with-at-least-32-characters",
            database_url="postgresql+asyncpg://u:p@localhost:5432/test",
            metrics_token="too-short",
            cors_allowed_origins="https://research.example.com",
        )


def test_database_url_removes_unsupported_channel_binding_parameter() -> None:
    settings = Settings(
        database_url=(
            "postgresql+asyncpg://u:p@neon.example/db"
            "?sslmode=require&channel_binding=require&application_name=market"
        )
    )
    assert "ssl=require" in settings.database_url
    assert "channel_binding" not in settings.database_url
    assert "application_name=market" in settings.database_url


def test_unpooled_database_url_uses_same_asyncpg_normalization() -> None:
    settings = Settings(
        database_url_unpooled=(
            "postgresql://u:p@neon.example/db?sslmode=verify-full&channel_binding=require"
        )
    )
    assert settings.database_url_unpooled is not None
    assert settings.database_url_unpooled.startswith("postgresql+asyncpg://")
    assert "ssl=verify-full" in settings.database_url_unpooled
    assert "channel_binding" not in settings.database_url_unpooled
