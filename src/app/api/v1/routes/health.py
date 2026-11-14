from __future__ import annotations

from fastapi import APIRouter, Depends
from psycopg_pool import AsyncConnectionPool

from app.core.config import Settings, get_settings
from app.core.database import get_pool
from app.repositories.health_repository import HealthRepository
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("", response_model=HealthResponse)
async def health_check(
    pool: AsyncConnectionPool | None = Depends(get_pool),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    repository = HealthRepository(pool)
    database_ok = await repository.ping()
    return HealthResponse(
        status="healthy" if database_ok else "degraded",
        version=settings.VERSION,
        dependencies={"database": database_ok},
    )
