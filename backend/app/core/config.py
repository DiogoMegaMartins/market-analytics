from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _normalize_asyncpg_url(value: str, setting_name: str) -> str:
    value = value.strip()
    if value.startswith("postgres://"):
        value = "postgresql+asyncpg://" + value[len("postgres://"): ]
    elif value.startswith("postgresql://"):
        value = "postgresql+asyncpg://" + value[len("postgresql://"): ]
    if not value.startswith("postgresql+asyncpg://"):
        raise ValueError(f"{setting_name} must use postgresql+asyncpg://")

    parsed = urlsplit(value)
    query = parse_qs(parsed.query, keep_blank_values=True)
    # asyncpg does not accept libpq's channel_binding connection parameter.
    query.pop("channel_binding", None)
    # Neon/libpq URLs commonly use sslmode; SQLAlchemy's asyncpg dialect uses ssl.
    if "sslmode" in query and "ssl" not in query:
        query["ssl"] = query.pop("sslmode")
    return urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urlencode(query, doseq=True), parsed.fragment)
    )


class Settings(BaseSettings):
    app_name: str = "Market Analytics API"
    app_env: str = "development"
    app_debug: bool = False
    database_url: str = (
        "postgresql+asyncpg://market:market_dev_password@localhost:5432/market_analytics"
    )
    database_url_unpooled: str | None = None
    secret_key: SecretStr = SecretStr("development-only-change-me")
    sec_user_agent: str = "MarketAnalytics contact@example.com"
    redis_url: str = "redis://localhost:6379/0"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout_seconds: int = 30
    sec_max_attempts: int = 3
    sec_retry_base_seconds: float = 0.5
    sec_retry_max_seconds: float = 8.0
    sec_company_facts_cache_ttl_seconds: int = 86400
    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    metrics_token: SecretStr = SecretStr("")
    openai_enabled: bool = False
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-5.5"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_timeout_seconds: float = 45.0
    openai_max_output_tokens: int = 2500

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("app_env")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"development", "test", "staging", "production"}:
            raise ValueError("APP_ENV must be development, test, staging or production")
        return normalized

    @field_validator("database_url")
    @classmethod
    def require_async_postgres_url(cls, value: str) -> str:
        return _normalize_asyncpg_url(value, "DATABASE_URL")

    @field_validator("database_url_unpooled")
    @classmethod
    def normalize_unpooled_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return _normalize_asyncpg_url(value, "DATABASE_URL_UNPOOLED")

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.app_env in {"staging", "production"}:
            if "database_url" not in self.model_fields_set:
                raise ValueError("DATABASE_URL must be explicitly configured outside development/test")
            parsed_db = urlsplit(self.database_url)
            query = parse_qs(parsed_db.query, keep_blank_values=True)
            is_local = parsed_db.hostname in {"localhost", "127.0.0.1", "::1"}
            if not is_local and query.get("ssl", [""])[0].lower() not in {"require", "verify-ca", "verify-full"}:
                raise ValueError("Remote PostgreSQL connections require TLS (ssl=require or stronger)")
            secret = self.secret_key.get_secret_value()
            if len(secret) < 32 or secret == "development-only-change-me":
                raise ValueError("SECRET_KEY must be a unique secret of at least 32 characters")
            if self.app_debug:
                raise ValueError("APP_DEBUG must be false outside development and test")
            metrics_token = self.metrics_token.get_secret_value()
            if metrics_token and len(metrics_token) < 32:
                raise ValueError("METRICS_TOKEN must contain at least 32 characters when configured")
            origins = [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]
            if not origins:
                raise ValueError("CORS_ALLOWED_ORIGINS must contain at least one explicit origin")
            for origin in origins:
                parsed = urlsplit(origin)
                if "*" in origin or parsed.scheme != "https" or not parsed.netloc or parsed.path != "" or parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
                    raise ValueError("Staging/production CORS origins must be explicit HTTPS origins without paths")
        if self.openai_enabled and not self.openai_api_key.get_secret_value().strip():
            raise ValueError("OPENAI_API_KEY is required when OPENAI_ENABLED=true")
        parsed_openai_url = urlsplit(self.openai_base_url)
        local_http_allowed = self.app_env in {"development", "test"} and parsed_openai_url.scheme == "http" and parsed_openai_url.hostname in {"localhost", "127.0.0.1"}
        if (not self.openai_model.strip() or not parsed_openai_url.netloc
                or (parsed_openai_url.scheme != "https" and not local_http_allowed)
                or parsed_openai_url.username is not None or parsed_openai_url.password is not None
                or parsed_openai_url.query or parsed_openai_url.fragment):
            raise ValueError("OpenAI model or base URL is invalid; use HTTPS outside local development")
        if self.openai_timeout_seconds <= 0 or self.openai_timeout_seconds > 300 or not 256 <= self.openai_max_output_tokens <= 16384:
            raise ValueError("OpenAI timeout and output-token limits are invalid")
        if self.database_pool_size < 1 or self.database_max_overflow < 0:
            raise ValueError("Database pool settings are invalid")
        if self.sec_max_attempts < 1 or self.sec_retry_base_seconds < 0:
            raise ValueError("SEC retry settings are invalid")
        if self.sec_retry_max_seconds < self.sec_retry_base_seconds:
            raise ValueError("SEC maximum backoff must be >= base backoff")
        if self.sec_company_facts_cache_ttl_seconds < 0:
            raise ValueError("SEC cache TTL cannot be negative")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
