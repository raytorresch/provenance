from app.domain.ports import ChunkSearchPort, EmbeddingProviderPort
from app.domain.entities import RetrievedChunk
from app.core.config import get_settings

class RetriveChunksUseCase():
    def __init__(
            self,
            embedder: EmbeddingProviderPort,
            repository: ChunkSearchPort
    ) -> None:
        self._repo = repository
        self._embedder = embedder

    def execute(self, query: str) -> list[RetrievedChunk] | str :
        settings = get_settings()

        vector = self._embedder.embed_query(query)

        if not vector:
            return "error str placeholder"

        return self._repo.find_similar_chunks(
            vector,
            settings.EMBEDDING_MODEL,
            "strategy_placeholder"
        )