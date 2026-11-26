from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.models.rag import Chunk, ChunkEmbedding, Document
from app.adapters.outbound.persistence.repositories.store_repository import (
    StoreRepository,
)
from app.domain.entities import (
    ChunkData,
    FetchDocumentPayload,
    SaveDocumentPayload,
    SaveOutcome,
)


def _payload(
    *,
    adr_code: str = "ADR-STORE-0001",
    title: str = "Store test ADR",
    source_url: str = "https://example.com/adr/store-0001",
    content_hash: str = "hash-v1",
    chunking_strategy: str = "by_heading_v1",
    model_name: str = "model-a",
    chunks: list[ChunkData] | None = None,
    embeddings: list[list[float]] | None = None,
) -> SaveDocumentPayload:
    chunks = chunks if chunks is not None else [
        ChunkData(
            ordinal=0,
            heading_path="Context",
            content="Original context.",
        ),
        ChunkData(
            ordinal=1,
            heading_path="Decision",
            content="Original decision.",
        ),
    ]
    embeddings = embeddings if embeddings is not None else [
        [1.0, 0.0, 0.0] for _ in chunks
    ]
    return SaveDocumentPayload(
        adr_code=adr_code,
        title=title,
        source_url=source_url,
        content_hash=content_hash,
        chunking_strategy=chunking_strategy,
        chunks=chunks,
        embeddings=embeddings,
        model_name=model_name,
    )


def _fetch_payload_for(
    payload: SaveDocumentPayload, *, model_name: str | None = None
) -> FetchDocumentPayload:
    return FetchDocumentPayload(
        adr_code=payload.adr_code,
        content_hash=payload.content_hash,
        chunking_strategy=payload.chunking_strategy,
        model_name=model_name or payload.model_name,
    )


def test_exists_by_keys_is_false_when_document_does_not_exist(
    db_session: Session,
) -> None:
    repo = StoreRepository(db_session)

    assert repo.exists_by_keys(_fetch_payload_for(_payload())) is False


def test_exists_by_keys_is_true_once_saved_with_matching_keys(
    db_session: Session,
) -> None:
    repo = StoreRepository(db_session)
    payload = _payload()

    repo.save_document_with_embeddings(payload)

    assert repo.exists_by_keys(_fetch_payload_for(payload)) is True


def test_exists_by_keys_is_false_for_a_different_model_name(
    db_session: Session,
) -> None:
    repo = StoreRepository(db_session)
    payload = _payload(model_name="model-a")

    repo.save_document_with_embeddings(payload)

    assert repo.exists_by_keys(_fetch_payload_for(payload, model_name="model-b")) is False


def test_save_new_document_inserts_document_chunks_and_embeddings(
    db_session: Session,
) -> None:
    repo = StoreRepository(db_session)
    payload = _payload()

    result = repo.save_document_with_embeddings(payload)

    assert result is SaveOutcome.INSERTED

    document = db_session.execute(
        select(Document).where(Document.adr_code == payload.adr_code)
    ).scalar_one()
    assert document.title == payload.title
    assert document.source_url == payload.source_url
    assert document.content_hash == payload.content_hash

    chunks = (
        db_session.execute(select(Chunk).where(Chunk.document_id == document.id))
        .scalars()
        .all()
    )
    assert {c.heading_path for c in chunks} == {"Context", "Decision"}

    embeddings = (
        db_session.execute(
            select(ChunkEmbedding).where(
                ChunkEmbedding.chunk_id.in_([c.id for c in chunks])
            )
        )
        .scalars()
        .all()
    )
    assert len(embeddings) == 2
    assert {e.model_name for e in embeddings} == {payload.model_name}


def test_save_with_changed_content_hash_replaces_chunks_and_embeddings(
    db_session: Session,
) -> None:
    repo = StoreRepository(db_session)
    original = _payload(content_hash="hash-v1")
    repo.save_document_with_embeddings(original)

    updated = _payload(
        content_hash="hash-v2",
        title="Updated title",
        chunks=[
            ChunkData(
                ordinal=0,
                heading_path="Context",
                content="Rewritten context.",
            )
        ],
        embeddings=[[0.0, 1.0, 0.0]],
    )

    result = repo.save_document_with_embeddings(updated)

    assert result is SaveOutcome.REPLACED

    document = db_session.execute(
        select(Document).where(Document.adr_code == original.adr_code)
    ).scalar_one()
    assert document.content_hash == "hash-v2"
    assert document.title == "Updated title"

    chunks = (
        db_session.execute(select(Chunk).where(Chunk.document_id == document.id))
        .scalars()
        .all()
    )
    # Old "Decision" chunk from hash-v1 must be gone, not just superseded.
    assert len(chunks) == 1
    assert chunks[0].heading_path == "Context"
    assert chunks[0].content == "Rewritten context."

    embeddings = (
        db_session.execute(
            select(ChunkEmbedding).where(ChunkEmbedding.chunk_id == chunks[0].id)
        )
        .scalars()
        .all()
    )
    assert len(embeddings) == 1
    assert embeddings[0].embedding == [0.0, 1.0, 0.0]


def test_save_with_same_content_new_strategy_adds_chunks_without_touching_others(
    db_session: Session,
) -> None:
    repo = StoreRepository(db_session)
    original = _payload(chunking_strategy="by_heading_v1", content_hash="hash-v1")
    repo.save_document_with_embeddings(original)

    new_strategy_payload = _payload(
        chunking_strategy="fixed_512_64",
        content_hash="hash-v1",
        chunks=[
            ChunkData(
                ordinal=0,
                heading_path="Context",
                content="Same content, different split.",
            )
        ],
        embeddings=[[0.5, 0.5, 0.0]],
    )

    result = repo.save_document_with_embeddings(new_strategy_payload)

    assert result is SaveOutcome.STRATEGY_ADDED

    document = db_session.execute(
        select(Document).where(Document.adr_code == original.adr_code)
    ).scalar_one()
    chunks = (
        db_session.execute(select(Chunk).where(Chunk.document_id == document.id))
        .scalars()
        .all()
    )
    strategies_present = {c.chunking_strategy for c in chunks}
    assert strategies_present == {"by_heading_v1", "fixed_512_64"}
    # The original strategy's chunks must still be exactly the original two.
    assert len([c for c in chunks if c.chunking_strategy == "by_heading_v1"]) == 2


def test_save_with_same_content_and_strategy_new_model_only_adds_embeddings(
    db_session: Session,
) -> None:
    repo = StoreRepository(db_session)
    original = _payload(model_name="model-a", content_hash="hash-v1")
    repo.save_document_with_embeddings(original)

    second_model_payload = _payload(
        model_name="model-b",
        content_hash="hash-v1",
        embeddings=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
    )

    result = repo.save_document_with_embeddings(second_model_payload)

    assert result is SaveOutcome.MODEL_ADDED

    document = db_session.execute(
        select(Document).where(Document.adr_code == original.adr_code)
    ).scalar_one()
    chunks = (
        db_session.execute(select(Chunk).where(Chunk.document_id == document.id))
        .scalars()
        .all()
    )
    # No duplicate chunks were created for the second model.
    assert len(chunks) == 2

    embeddings = (
        db_session.execute(
            select(ChunkEmbedding).where(
                ChunkEmbedding.chunk_id.in_([c.id for c in chunks])
            )
        )
        .scalars()
        .all()
    )
    assert len(embeddings) == 4
    assert {e.model_name for e in embeddings} == {"model-a", "model-b"}

    by_ordinal_and_model = {
        (chunk.ordinal, embedding.model_name): embedding.embedding
        for chunk in chunks
        for embedding in embeddings
        if embedding.chunk_id == chunk.id
    }
    assert by_ordinal_and_model[(0, "model-b")] == [0.1, 0.2, 0.3]
    assert by_ordinal_and_model[(1, "model-b")] == [0.4, 0.5, 0.6]


def test_save_with_same_content_and_strategy_raises_on_unmatched_ordinal(
    db_session: Session,
) -> None:
    """A payload that claims the same content and strategy as what's already
    stored, but with a chunk ordinal that has no matching row, is a
    payload/DB inconsistency. It must fail loudly instead of silently
    dropping that chunk's embedding."""
    repo = StoreRepository(db_session)
    original = _payload(content_hash="hash-v1")  # ordinals 0 and 1
    repo.save_document_with_embeddings(original)

    inconsistent_payload = _payload(
        model_name="model-b",
        content_hash="hash-v1",
        chunks=[
            ChunkData(ordinal=0, heading_path="Context", content="Original context."),
            ChunkData(ordinal=99, heading_path="Nowhere", content="No matching chunk."),
        ],
        embeddings=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
    )

    with pytest.raises(ValueError, match="99"):
        repo.save_document_with_embeddings(inconsistent_payload)
