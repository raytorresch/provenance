from __future__ import annotations

from collections.abc import AsyncIterator

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from app.core.config import get_settings

_pool: AsyncConnectionPool | None = None


def get_sqlalchemy_url() -> str:
    url = get_settings().VECTOR_DB_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


async def init_db_pool() -> None:
    global _pool
    settings = get_settings()
    if not settings.VECTOR_DB_URL:
        raise RuntimeError("VECTOR_DB_URL is not configured.")
    _pool = AsyncConnectionPool(conninfo=settings.VECTOR_DB_URL, open=False)
    await _pool.open()


async def close_db_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> AsyncConnectionPool | None:
    return _pool


async def get_db_connection() -> AsyncIterator[AsyncConnection]:
    pool = get_pool()
    if pool is None:
        raise RuntimeError("Database pool is not initialized.")
    async with pool.connection() as connection:
        yield connection
