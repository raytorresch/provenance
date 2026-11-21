from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.rag import Chunk, ChunkEmbedding, Document


def test_check_constraint_rejects_mismatched_dimensions(db_session: Session) -> None:
    document = Document(
        adr_code="ADR-TEST-DIMS",
        title="Integration test ADR",
        source_url="https://example.com/adr/dims",
        content_hash="test-hash-dims",
    )
    chunk = Chunk(
        ordinal=0,
        chunking_strategy="by_heading_v1",
        heading_path="Context",
        content="Chunk content.",
        document=document,
    )
    embedding = ChunkEmbedding(
        chunk=chunk,
        model_name="fake-model",
        dimensions=5,
        embedding=[0.1, 0.2, 0.3],
    )

    db_session.add_all([document, chunk, embedding])

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()
