from app.domain.chunking import DEFAULT_MAX_CHARS, build_chunking_strategy
from app.domain.entities import RetrievedChunk
from app.domain.ports import ChunkSearchPort, EmbeddingProviderPort


class RetrieveChunksUseCase:
    def __init__(
        self,
        embedder: EmbeddingProviderPort,
        repository: ChunkSearchPort,
        max_chars: int = DEFAULT_MAX_CHARS,
        contextual_header: bool = True,
    ) -> None:
        self._embedder = embedder
        self._repo = repository
        # Must match the strategy label chunks were ingested under
        # (app.application.ingest_adr), or find_similar_chunks finds nothing.
        self._chunking_strategy = build_chunking_strategy(
            max_chars=max_chars, contextual_header=contextual_header
        )

    def execute(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        """Embebe la pregunta y recupera los chunks más similares."""
        query_embedding = self._embedder.embed_query(query)
        return self._repo.find_similar_chunks(
            query_embedding,
            self._embedder.model_name,
            self._chunking_strategy,
            top_k=top_k,
        )
