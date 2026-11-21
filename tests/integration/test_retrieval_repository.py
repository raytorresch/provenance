from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.rag import Chunk, ChunkEmbedding, Document
from app.repositories.retrieval_repository import RetrievalRepository


def test_find_similar_chunks_filters_by_model_name(db_session: Session) -> None:
    document = Document(
        adr_code="ADR-TEST-RETRIEVAL",
        title="Integration test ADR",
        source_url="https://example.com/adr/retrieval",
        content_hash="test-hash-retrieval",
    )
    chunk_a = Chunk(
        ordinal=0,
        chunking_strategy="by_heading_v1",
        heading_path="Context",
        content="Chunk embedded with model A.",
        document=document,
    )
    chunk_b = Chunk(
        ordinal=1,
        chunking_strategy="by_heading_v1",
        heading_path="Decision",
        content="Chunk embedded with model B.",
        document=document,
    )
    # Identical vectors on purpose: if the query didn't filter by model_name,
    # chunk_b would be an equally valid (or better) match for a model-a query.
    embedding_a = ChunkEmbedding(
        chunk=chunk_a, model_name="model-a", dimensions=3, embedding=[1.0, 0.0, 0.0]
    )
    embedding_b = ChunkEmbedding(
        chunk=chunk_b, model_name="model-b", dimensions=3, embedding=[1.0, 0.0, 0.0]
    )

    db_session.add_all([document, chunk_a, chunk_b, embedding_a, embedding_b])
    db_session.flush()

    repository = RetrievalRepository(db_session)
    results = repository.find_similar_chunks(
        query_embedding=[1.0, 0.0, 0.0], model_name="model-a", limit=5
    )

    assert [chunk.id for chunk in results] == [chunk_a.id]
