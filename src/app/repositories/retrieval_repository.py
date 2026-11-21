from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rag import Chunk, ChunkEmbedding


class RetrievalRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_similar_chunks(
        self, query_embedding: list[float], model_name: str, limit: int = 5
    ) -> list[Chunk]:
        # Comparing vectors from different models is both meaningless and,
        # since dimensions can differ, an error at the database level.
        stmt = (
            select(Chunk)
            .join(ChunkEmbedding)
            .where(ChunkEmbedding.model_name == model_name)
            .order_by(ChunkEmbedding.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        return list(self._session.scalars(stmt))
