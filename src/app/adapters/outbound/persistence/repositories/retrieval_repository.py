from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.models.rag import Chunk, ChunkEmbedding, Document
from app.domain.entities import RetrievedChunk


class RetrievalRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_similar_chunks(
        self,
        query_embedding: list[float],
        model_name: str,
        chunking_strategy: str,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        # pgvector's cosine_distance() is 1 - cosine_similarity, so we flip
        # it back to a similarity score before crossing the port boundary.
        distance = ChunkEmbedding.embedding.cosine_distance(query_embedding)

        # Comparing vectors from different models is both meaningless and,
        # since dimensions can differ, an error at the database level.
        stmt = (
            select(
                Document.adr_code,
                Document.title,
                Chunk.heading_path,
                Chunk.content,
                distance.label("distance"),
            )
            .select_from(ChunkEmbedding)
            .join(Chunk, Chunk.id == ChunkEmbedding.chunk_id)
            .join(Document, Document.id == Chunk.document_id)
            .where(ChunkEmbedding.model_name == model_name)
            .where(Chunk.chunking_strategy == chunking_strategy)
            .order_by(distance)
            .limit(top_k)
        )
        rows = self._session.execute(stmt).all()
        return [
            RetrievedChunk(
                adr_code=row.adr_code,
                title=row.title,
                heading_path=row.heading_path,
                content=row.content,
                similarity=1.0 - row.distance,
            )
            for row in rows
        ]
