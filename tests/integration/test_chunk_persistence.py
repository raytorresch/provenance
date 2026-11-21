from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.rag import Chunk, Document


def test_insert_and_read_back_chunk(db_session: Session) -> None:
    document = Document(
        adr_code="ADR-TEST-0001",
        title="Integration test ADR",
        source_url="https://example.com/adr/0001",
        content_hash="test-hash-0001",
    )
    chunk = Chunk(
        ordinal=0,
        chunking_strategy="by_heading_v1",
        heading_path="Context",
        content="This chunk is written by an integration test.",
        document=document,
    )

    db_session.add(document)
    db_session.add(chunk)
    db_session.flush()

    chunk_id = chunk.id
    db_session.expire_all()  # force the next get() to hit Postgres, not the identity map

    stored = db_session.get(Chunk, chunk_id)

    assert stored is not None
    assert stored.document_id == document.id
    assert stored.ordinal == 0
    assert stored.chunking_strategy == "by_heading_v1"
    assert stored.heading_path == "Context"
    assert stored.content == "This chunk is written by an integration test."
