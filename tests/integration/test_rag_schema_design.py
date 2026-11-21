from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.rag import Chunk, ChunkEmbedding, Document


def test_chunk_embeddings_support_multiple_dimensions_per_document(
    db_session: Session,
) -> None:
    document = Document(
        adr_code="ADR-TEST-MULTI-DIM",
        title="Integration test ADR",
        source_url="https://example.com/adr/multi-dim",
        content_hash="test-hash-multi-dim",
    )
    chunk = Chunk(
        ordinal=0,
        chunking_strategy="by_heading_v1",
        heading_path="Context",
        content="Chunk content.",
        document=document,
    )
    embedding_3072 = ChunkEmbedding(
        chunk=chunk,
        model_name="gemini-embedding-001",
        dimensions=3072,
        embedding=[0.001] * 3072,
    )
    embedding_768 = ChunkEmbedding(
        chunk=chunk,
        model_name="text-embedding-3-small",
        dimensions=768,
        embedding=[0.002] * 768,
    )

    db_session.add_all([document, chunk, embedding_3072, embedding_768])
    db_session.flush()
    db_session.expire_all()

    stored = db_session.get(Chunk, chunk.id)
    by_dimensions = {e.dimensions: e for e in stored.embeddings}

    assert set(by_dimensions) == {768, 3072}
    assert len(by_dimensions[3072].embedding) == 3072
    assert len(by_dimensions[768].embedding) == 768


def test_unique_constraint_rejects_duplicate_chunk_ordinal_per_strategy(
    db_session: Session,
) -> None:
    document = Document(
        adr_code="ADR-TEST-DUP-ORDINAL",
        title="Integration test ADR",
        source_url="https://example.com/adr/dup-ordinal",
        content_hash="test-hash-dup-ordinal",
    )
    first = Chunk(
        ordinal=0,
        chunking_strategy="by_heading_v1",
        heading_path="Context",
        content="First chunk.",
        document=document,
    )
    db_session.add_all([document, first])
    db_session.flush()

    duplicate = Chunk(
        document_id=document.id,
        ordinal=0,
        chunking_strategy="by_heading_v1",
        heading_path="Context (duplicate)",
        content="Duplicate chunk.",
    )

    # The flush aborts the transaction, so the duplicate insert runs inside
    # a SAVEPOINT: pytest.raises catches the error and the SAVEPOINT rollback
    # leaves the outer session transaction (and `first`) usable afterward.
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(duplicate)
        db_session.flush()


def test_unique_constraint_rejects_duplicate_embedding_model_per_chunk(
    db_session: Session,
) -> None:
    document = Document(
        adr_code="ADR-TEST-DUP-MODEL",
        title="Integration test ADR",
        source_url="https://example.com/adr/dup-model",
        content_hash="test-hash-dup-model",
    )
    chunk = Chunk(
        ordinal=0,
        chunking_strategy="by_heading_v1",
        heading_path="Context",
        content="Chunk content.",
        document=document,
    )
    embedding = ChunkEmbedding(
        chunk=chunk, model_name="model-a", dimensions=3, embedding=[1.0, 0.0, 0.0]
    )
    db_session.add_all([document, chunk, embedding])
    db_session.flush()

    duplicate_embedding = ChunkEmbedding(
        chunk_id=chunk.id,
        model_name="model-a",
        dimensions=3,
        embedding=[0.0, 1.0, 0.0],
    )

    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(duplicate_embedding)
        db_session.flush()


def test_deleting_document_cascades_to_chunks_and_embeddings(
    db_session: Session,
) -> None:
    document = Document(
        adr_code="ADR-TEST-CASCADE",
        title="Integration test ADR",
        source_url="https://example.com/adr/cascade",
        content_hash="test-hash-cascade",
    )
    chunk = Chunk(
        ordinal=0,
        chunking_strategy="by_heading_v1",
        heading_path="Context",
        content="Chunk content.",
        document=document,
    )
    embedding = ChunkEmbedding(
        chunk=chunk, model_name="model-a", dimensions=3, embedding=[1.0, 0.0, 0.0]
    )
    db_session.add_all([document, chunk, embedding])
    db_session.flush()

    document_id = document.id
    chunk_id = chunk.id
    embedding_id = embedding.id

    # Raw SQL, bypassing the ORM's own delete-orphan cascade, so this proves
    # the database's ON DELETE CASCADE actually enforces it, not just the
    # SQLAlchemy relationship config.
    db_session.execute(text("DELETE FROM documents WHERE id = :id"), {"id": document_id})
    db_session.expire_all()

    assert db_session.get(Document, document_id) is None
    assert db_session.get(Chunk, chunk_id) is None
    assert db_session.get(ChunkEmbedding, embedding_id) is None
