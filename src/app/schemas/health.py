from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(
        ...,
        description="'healthy' all works, 'degraded' something failed",
    )
    version: str
    dependencies: dict[str, bool] = Field(
        ..., description="Dependencies status (database, ...)"
    )
