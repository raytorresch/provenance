from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(
        ...,
        description="'healthy' all works, 'degraded' something failed",
    )
    version: str
    dependencies: Dict[str, bool] = Field(
        ..., description="Dependencies status (database, ...)"
    )
