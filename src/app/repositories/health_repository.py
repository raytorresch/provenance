from __future__ import annotations

import logging

from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)


class HealthRepository:
    def __init__(self, pool: AsyncConnectionPool | None) -> None:
        self._pool = pool

    async def ping(self) -> bool:
        if self._pool is None:
            return False
        try:
            async with self._pool.connection() as connection, connection.cursor() as cursor:
                await cursor.execute("SELECT 1")
                result = await cursor.fetchone()
            return result == (1,)
        except Exception:
            logger.exception("Database ping failed")
            return False
