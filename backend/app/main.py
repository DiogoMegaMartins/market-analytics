import hmac
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.observability import RequestMetricsMiddleware, database_pool_metrics, metrics
from app.platform.database.session import dispose_database, ping_database, verify_database_schema

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await dispose_database()


app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RequestMetricsMiddleware)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health/live", tags=["health"])
async def live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready", tags=["health"])
async def ready() -> dict[str, str]:
    try:
        await ping_database()
        schema_revision = await verify_database_schema()
    except (SQLAlchemyError, OSError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database or schema is not ready",
        ) from exc
    return {"status": "ready", "database": "connected", "schema": "current", "schema_revision": schema_revision}


@app.get("/metrics", tags=["operations"], include_in_schema=False)
async def prometheus_metrics(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> PlainTextResponse:
    configured_token = settings.metrics_token.get_secret_value()
    if settings.app_env in {"staging", "production"}:
        if not configured_token:
            raise HTTPException(status_code=404, detail="Not found")
        expected = f"Bearer {configured_token}"
        if authorization is None or not hmac.compare_digest(authorization, expected):
            raise HTTPException(status_code=401, detail="Metrics authentication required")
    return PlainTextResponse(
        metrics.render(pool=database_pool_metrics()),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
