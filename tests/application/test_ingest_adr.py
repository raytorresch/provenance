from __future__ import annotations

import hashlib

import pytest

from app.application.ingest_adr import IngestAdrUseCase, IngestOutcome
from app.domain.chunking import build_chunking_strategy, chunk_markdown
from app.domain.entities import (
    DocumentInput,
    FetchDocumentPayload,
    SaveDocumentPayload,
    SaveOutcome,
)


class _FakeRepository:
    def __init__(
        self, exists: bool = False, save_outcome: SaveOutcome = SaveOutcome.INSERTED
    ) -> None:
        self._exists = exists
        self._save_outcome = save_outcome
        self.exists_calls: list[FetchDocumentPayload] = []
        self.save_calls: list[SaveDocumentPayload] = []

    def exists_by_keys(self, payload: FetchDocumentPayload) -> bool:
        self.exists_calls.append(payload)
        return self._exists

    def save_document_with_embeddings(
        self, payload: SaveDocumentPayload
    ) -> SaveOutcome:
        self.save_calls.append(payload)
        return self._save_outcome


class _FakeEmbedder:
    def __init__(self) -> None:
        self.call_count = 0
        self.received_texts: list[str] = []

    @property
    def model_name(self) -> str:
        return "fake-model"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.call_count += 1
        self.received_texts = texts
        return [[float(i)] for i in range(len(texts))]


class _MismatchedEmbedder:
    """Simulates a misbehaving embedding provider that returns the wrong
    number of vectors for the texts it was given."""

    @property
    def model_name(self) -> str:
        return "mismatched-model"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.0]] if texts else []


def _make_doc(raw_markdown: str) -> DocumentInput:
    return DocumentInput(
        adr_code="ADR-0001",
        title="A decision",
        source_url="https://example.com/adr/0001",
        raw_markdown=raw_markdown,
    )


def test_execute_returns_already_exists_and_skips_embedding() -> None:
    repo = _FakeRepository(exists=True)
    embedder = _FakeEmbedder()

    result = IngestAdrUseCase(repo, embedder).execute(
        _make_doc("# Title\nSome content.")
    )

    assert result is IngestOutcome.ALREADY_EXISTS
    assert embedder.call_count == 0
    assert repo.save_calls == []


def test_execute_checks_existence_by_adr_code_hash_strategy_and_model() -> None:
    repo = _FakeRepository(exists=True)
    embedder = _FakeEmbedder()
    doc = _make_doc("# Title\nSome content.")
    expected_hash = hashlib.sha256(doc.raw_markdown.encode("utf-8")).hexdigest()
    expected_strategy = build_chunking_strategy(contextual_header=True)

    IngestAdrUseCase(repo, embedder).execute(doc)

    assert len(repo.exists_calls) == 1
    checked = repo.exists_calls[0]
    assert checked.adr_code == doc.adr_code
    assert checked.content_hash == expected_hash
    assert checked.chunking_strategy == expected_strategy
    assert checked.model_name == "fake-model"


def test_execute_returns_no_content_when_markdown_produces_no_chunks() -> None:
    repo = _FakeRepository(exists=False)
    embedder = _FakeEmbedder()

    result = IngestAdrUseCase(repo, embedder).execute(_make_doc("   \n\n  "))

    assert result is IngestOutcome.NO_CONTENT
    assert embedder.call_count == 0
    assert repo.save_calls == []


def test_execute_injects_heading_path_before_embedding_by_default() -> None:
    repo = _FakeRepository(exists=False)
    embedder = _FakeEmbedder()
    doc = _make_doc("# Title\nSome content.")

    IngestAdrUseCase(repo, embedder).execute(doc)

    assert embedder.received_texts == ["Title\n\nSome content."]


def test_execute_skips_header_injection_when_disabled() -> None:
    repo = _FakeRepository(exists=False)
    embedder = _FakeEmbedder()
    doc = _make_doc("# Title\nSome content.")

    IngestAdrUseCase(repo, embedder, contextual_header=False).execute(doc)

    assert embedder.received_texts == ["Some content."]


def test_execute_persists_hash_strategy_chunks_embeddings_and_returns_save_outcome() -> (
    None
):
    repo = _FakeRepository(exists=False, save_outcome=SaveOutcome.INSERTED)
    embedder = _FakeEmbedder()
    doc = _make_doc("# Title\nSome content.")
    expected_hash = hashlib.sha256(doc.raw_markdown.encode("utf-8")).hexdigest()
    expected_chunks = chunk_markdown(doc.raw_markdown)
    expected_strategy = build_chunking_strategy(contextual_header=True)

    result = IngestAdrUseCase(repo, embedder).execute(doc)

    # The use case forwards exactly what the repository reports, instead of
    # collapsing every successful save into a generic "saved".
    assert result is SaveOutcome.INSERTED
    assert len(repo.save_calls) == 1
    call = repo.save_calls[0]
    assert call.adr_code == doc.adr_code
    assert call.title == doc.title
    assert call.source_url == doc.source_url
    assert call.content_hash == expected_hash
    assert call.chunking_strategy == expected_strategy
    assert call.chunks == expected_chunks
    assert call.embeddings == [[0.0]]
    assert call.model_name == "fake-model"


def test_execute_forwards_whatever_save_outcome_the_repository_reports() -> None:
    repo = _FakeRepository(exists=False, save_outcome=SaveOutcome.MODEL_ADDED)
    embedder = _FakeEmbedder()
    doc = _make_doc("# Title\nSome content.")

    result = IngestAdrUseCase(repo, embedder).execute(doc)

    assert result is SaveOutcome.MODEL_ADDED


def test_execute_raises_before_saving_when_vector_count_does_not_match_chunk_count() -> (
    None
):
    repo = _FakeRepository(exists=False)
    embedder = _MismatchedEmbedder()
    doc = _make_doc("# Title\nFirst.\n## Other\nSecond.")  # 2 chunks

    with pytest.raises(ValueError, match="vectors"):
        IngestAdrUseCase(repo, embedder).execute(doc)

    # Caught in the use case, before the repository/session is ever touched.
    assert repo.save_calls == []


def test_execute_with_different_max_chars_produces_a_different_strategy_label() -> None:
    repo = _FakeRepository(exists=False)
    embedder = _FakeEmbedder()
    doc = _make_doc("# Title\nSome content.")

    IngestAdrUseCase(repo, embedder, max_chars=500).execute(doc)

    assert repo.save_calls[0].chunking_strategy == build_chunking_strategy(
        500, contextual_header=True
    )
