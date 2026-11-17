from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.schema import EXPECTED_ALEMBIC_REVISION


@lru_cache(maxsize=1)
def get_engine():
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=settings.app_debug,
        pool_pre_ping=True,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout_seconds,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with get_session_factory()() as session:
        yield session


async def ping_database() -> None:
    async with get_engine().connect() as connection:
        await connection.execute(text("SELECT 1"))


async def verify_database_schema() -> str:
    async with get_engine().connect() as connection:
        result = await connection.execute(text("SELECT version_num FROM alembic_version"))
        revisions = {str(row[0]) for row in result}
    if revisions != {EXPECTED_ALEMBIC_REVISION}:
        raise RuntimeError(f"Database schema revision is {revisions or 'missing'}; expected {EXPECTED_ALEMBIC_REVISION}")
    return EXPECTED_ALEMBIC_REVISION


async def dispose_database() -> None:
    if get_engine.cache_info().currsize:
        await get_engine().dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
