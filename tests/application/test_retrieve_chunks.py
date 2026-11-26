from __future__ import annotations

from app.application.retrieve import RetrieveChunksUseCase
from app.domain.chunking import build_chunking_strategy
from app.domain.entities import RetrievedChunk


class _FakeEmbedder:
    def __init__(self) -> None:
        self.received_queries: list[str] = []

    @property
    def model_name(self) -> str:
        return "fake-model"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("RetrieveChunksUseCase only embeds a single query")

    def embed_query(self, text: str) -> list[float]:
        self.received_queries.append(text)
        return [float(len(text))]


class _FakeChunkSearchRepository:
    def __init__(self, chunks: list[RetrievedChunk] | None = None) -> None:
        self._chunks = chunks if chunks is not None else []
        self.calls: list[dict[str, object]] = []

    def find_similar_chunks(
        self,
        query_embedding: list[float],
        model_name: str,
        chunking_strategy: str,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        self.calls.append(
            {
                "query_embedding": query_embedding,
                "model_name": model_name,
                "chunking_strategy": chunking_strategy,
                "top_k": top_k,
            }
        )
        return self._chunks


def _chunk(adr_code: str) -> RetrievedChunk:
    return RetrievedChunk(
        adr_code=adr_code,
        title="A decision",
        heading_path="Decision",
        content="Some content.",
        similarity=0.9,
    )


def test_execute_embeds_the_query_with_embed_query() -> None:
    embedder = _FakeEmbedder()
    repo = _FakeChunkSearchRepository()

    RetrieveChunksUseCase(embedder, repo).execute("what did we decide?")

    assert embedder.received_queries == ["what did we decide?"]


def test_execute_passes_the_query_embedding_model_name_and_chunking_strategy() -> None:
    embedder = _FakeEmbedder()
    repo = _FakeChunkSearchRepository()
    expected_strategy = build_chunking_strategy(contextual_header=True)

    RetrieveChunksUseCase(embedder, repo).execute("what did we decide?")

    assert len(repo.calls) == 1
    call = repo.calls[0]
    assert call["query_embedding"] == [float(len("what did we decide?"))]
    assert call["model_name"] == "fake-model"
    assert call["chunking_strategy"] == expected_strategy


def test_execute_defaults_top_k_to_five() -> None:
    embedder = _FakeEmbedder()
    repo = _FakeChunkSearchRepository()

    RetrieveChunksUseCase(embedder, repo).execute("query")

    assert repo.calls[0]["top_k"] == 5


def test_execute_forwards_a_custom_top_k() -> None:
    embedder = _FakeEmbedder()
    repo = _FakeChunkSearchRepository()

    RetrieveChunksUseCase(embedder, repo).execute("query", top_k=10)

    assert repo.calls[0]["top_k"] == 10


def test_execute_returns_whatever_chunks_the_repository_finds() -> None:
    expected_chunks = [_chunk("ADR-0001"), _chunk("ADR-0002")]
    embedder = _FakeEmbedder()
    repo = _FakeChunkSearchRepository(chunks=expected_chunks)

    result = RetrieveChunksUseCase(embedder, repo).execute("query")

    assert result == expected_chunks


def test_execute_uses_a_chunking_strategy_matching_non_default_ingestion_settings() -> (
    None
):
    embedder = _FakeEmbedder()
    repo = _FakeChunkSearchRepository()
    expected_strategy = build_chunking_strategy(500, contextual_header=False)

    RetrieveChunksUseCase(
        embedder, repo, max_chars=500, contextual_header=False
    ).execute("query")

    assert repo.calls[0]["chunking_strategy"] == expected_strategy
