from __future__ import annotations

import hashlib

from app.application.ingest_adr import IngestAdrUseCase
from app.domain.chunking import chunk_markdown
from app.domain.entities import ChunkData, DocumentInput, RetrievedChunk


class _FakeRepository:
    def __init__(self, exists: bool = False) -> None:
        self._exists = exists
        self.save_calls: list[dict] = []

    def exists_by_hash(self, content_hash: str) -> bool:
        return self._exists

    def save_document_with_embeddings(
        self,
        adr_code: str,
        title: str,
        source_url: str,
        content_hash: str,
        chunks: list[ChunkData],
        embeddings: list[list[float]],
        model_name: str,
    ) -> int:
        self.save_calls.append(
            {
                "adr_code": adr_code,
                "title": title,
                "source_url": source_url,
                "content_hash": content_hash,
                "chunks": chunks,
                "embeddings": embeddings,
                "model_name": model_name,
            }
        )
        return len(self.save_calls)

    def search_similar(
        self,
        query_embedding: list[float],
        model_name: str,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        raise NotImplementedError


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


def _make_doc(raw_markdown: str) -> DocumentInput:
    return DocumentInput(
        adr_code="ADR-0001",
        title="A decision",
        source_url="https://example.com/adr/0001",
        raw_markdown=raw_markdown,
    )


def test_execute_returns_false_and_skips_embedding_when_document_already_exists() -> None:
    repo = _FakeRepository(exists=True)
    embedder = _FakeEmbedder()

    result = IngestAdrUseCase(repo, embedder).execute(_make_doc("# Title\nSome content."))

    assert result is False
    assert embedder.call_count == 0
    assert repo.save_calls == []


def test_execute_returns_false_when_markdown_produces_no_chunks() -> None:
    repo = _FakeRepository(exists=False)
    embedder = _FakeEmbedder()

    result = IngestAdrUseCase(repo, embedder).execute(_make_doc("   \n\n  "))

    assert result is False
    assert embedder.call_count == 0
    assert repo.save_calls == []


def test_execute_injects_heading_path_before_embedding() -> None:
    repo = _FakeRepository(exists=False)
    embedder = _FakeEmbedder()
    doc = _make_doc("# Title\nSome content.")

    IngestAdrUseCase(repo, embedder).execute(doc)

    assert embedder.received_texts == ["Title\n\nSome content."]


def test_execute_persists_hash_chunks_embeddings_and_returns_true() -> None:
    repo = _FakeRepository(exists=False)
    embedder = _FakeEmbedder()
    doc = _make_doc("# Title\nSome content.")
    expected_hash = hashlib.sha256(doc.raw_markdown.encode("utf-8")).hexdigest()
    expected_chunks = chunk_markdown(doc.raw_markdown)

    result = IngestAdrUseCase(repo, embedder).execute(doc)

    assert result is True
    assert len(repo.save_calls) == 1
    call = repo.save_calls[0]
    assert call["adr_code"] == doc.adr_code
    assert call["title"] == doc.title
    assert call["source_url"] == doc.source_url
    assert call["content_hash"] == expected_hash
    assert call["chunks"] == expected_chunks
    assert call["embeddings"] == [[0.0]]
    assert call["model_name"] == "fake-model"
