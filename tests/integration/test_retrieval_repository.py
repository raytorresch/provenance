from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.models.rag import Chunk, ChunkEmbedding, Document
from app.adapters.outbound.persistence.repositories.retrieval_repository import (
    RetrievalRepository,
)


def _to_vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(repr(float(v)) for v in embedding) + "]"


def _raw_cosine_order(
    session: Session,
    query_embedding: list[float],
    model_name: str,
    chunking_strategy: str,
    top_k: int,
) -> list[str]:
    """Same lookup as RetrievalRepository, but written with text() and the
    raw `<=>` pgvector operator instead of the ORM's cosine_distance()
    helper, so a test can check that the helper isn't hiding a different
    operator or a different sort order."""
    stmt = text(
        """
        SELECT c.heading_path AS heading_path
        FROM chunk_embeddings ce
        JOIN chunks c ON c.id = ce.chunk_id
        WHERE ce.model_name = :model_name
          AND c.chunking_strategy = :chunking_strategy
        ORDER BY ce.embedding <=> CAST(:query_embedding AS vector)
        LIMIT :top_k
        """
    )
    rows = session.execute(
        stmt,
        {
            "model_name": model_name,
            "chunking_strategy": chunking_strategy,
            "query_embedding": _to_vector_literal(query_embedding),
            "top_k": top_k,
        },
    ).all()
    return [row.heading_path for row in rows]


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
        query_embedding=[1.0, 0.0, 0.0],
        model_name="model-a",
        chunking_strategy="by_heading_v1",
        top_k=5,
    )

    assert len(results) == 1
    retrieved = results[0]
    assert retrieved.adr_code == "ADR-TEST-RETRIEVAL"
    assert retrieved.title == "Integration test ADR"
    assert retrieved.heading_path == "Context"
    assert retrieved.content == "Chunk embedded with model A."
    assert retrieved.similarity == 1.0


def test_find_similar_chunks_filters_by_chunking_strategy(db_session: Session) -> None:
    document = Document(
        adr_code="ADR-TEST-STRATEGY",
        title="Strategy test ADR",
        source_url="https://example.com/adr/strategy",
        content_hash="test-hash-strategy",
    )
    # Same content chunked twice under two strategies: without the
    # chunking_strategy filter, a query for "by_heading_v1" would also
    # return the "fixed_512_64" duplicate of the same text.
    chunk_by_heading = Chunk(
        ordinal=0,
        chunking_strategy="by_heading_v1",
        heading_path="Context",
        content="Duplicated content, chunked by heading.",
        document=document,
    )
    chunk_fixed_size = Chunk(
        ordinal=0,
        chunking_strategy="fixed_512_64",
        heading_path="Context",
        content="Duplicated content, chunked by fixed size.",
        document=document,
    )
    embedding_by_heading = ChunkEmbedding(
        chunk=chunk_by_heading,
        model_name="model-a",
        dimensions=3,
        embedding=[1.0, 0.0, 0.0],
    )
    embedding_fixed_size = ChunkEmbedding(
        chunk=chunk_fixed_size,
        model_name="model-a",
        dimensions=3,
        embedding=[1.0, 0.0, 0.0],
    )

    db_session.add_all(
        [
            document,
            chunk_by_heading,
            chunk_fixed_size,
            embedding_by_heading,
            embedding_fixed_size,
        ]
    )
    db_session.flush()

    repository = RetrievalRepository(db_session)
    results = repository.find_similar_chunks(
        query_embedding=[1.0, 0.0, 0.0],
        model_name="model-a",
        chunking_strategy="by_heading_v1",
        top_k=5,
    )

    assert len(results) == 1
    assert results[0].content == "Duplicated content, chunked by heading."


def test_find_similar_chunks_matches_raw_cosine_distance_order(
    db_session: Session,
) -> None:
    document = Document(
        adr_code="ADR-TEST-RAW-ORDER",
        title="Raw order ADR",
        source_url="https://example.com/adr/raw-order",
        content_hash="test-hash-raw-order",
    )
    chunk_close = Chunk(
        ordinal=0,
        chunking_strategy="by_heading_v1",
        heading_path="Closest",
        content="Vector almost identical to the query.",
        document=document,
    )
    chunk_mid = Chunk(
        ordinal=1,
        chunking_strategy="by_heading_v1",
        heading_path="Middle",
        content="Vector somewhat similar to the query.",
        document=document,
    )
    chunk_far = Chunk(
        ordinal=2,
        chunking_strategy="by_heading_v1",
        heading_path="Farthest",
        content="Vector far from the query.",
        document=document,
    )
    embedding_close = ChunkEmbedding(
        chunk=chunk_close,
        model_name="model-a",
        dimensions=3,
        embedding=[0.98, 0.02, 0.0],
    )
    embedding_mid = ChunkEmbedding(
        chunk=chunk_mid, model_name="model-a", dimensions=3, embedding=[0.6, 0.4, 0.0]
    )
    embedding_far = ChunkEmbedding(
        chunk=chunk_far, model_name="model-a", dimensions=3, embedding=[0.0, 0.0, 1.0]
    )

    db_session.add_all(
        [
            document,
            chunk_close,
            chunk_mid,
            chunk_far,
            embedding_close,
            embedding_mid,
            embedding_far,
        ]
    )
    db_session.flush()

    query_embedding = [1.0, 0.0, 0.0]
    repository = RetrievalRepository(db_session)

    orm_order = [
        chunk.heading_path
        for chunk in repository.find_similar_chunks(
            query_embedding=query_embedding,
            model_name="model-a",
            chunking_strategy="by_heading_v1",
            top_k=3,
        )
    ]
    raw_order = _raw_cosine_order(
        db_session,
        query_embedding=query_embedding,
        model_name="model-a",
        chunking_strategy="by_heading_v1",
        top_k=3,
    )

    assert orm_order == ["Closest", "Middle", "Farthest"]
    assert raw_order == orm_order
