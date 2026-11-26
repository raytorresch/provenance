from pathlib import Path
from typing import Protocol

from app.domain.entities import (
    FetchDocumentPayload,
    RetrievedChunk,
    SaveDocumentPayload,
    SaveOutcome,
)


class DocumentExtractorPort(Protocol):
    """Puerto de salida para extraer texto Markdown desde cualquier origen."""

    def extract_markdown(self, source: Path) -> str: ...


class EmbeddingProviderPort(Protocol):
    """Puerto de salida para generar vectores sin acoplarse a Gemini/OpenAI/Local."""

    @property
    def model_name(self) -> str: ...

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class ChunkSearchPort(Protocol):
    """Puerto de fetch"""

    def find_similar_chunks(
        self,
        query_embedding: list[float],
        model_name: str,
        chunking_strategy: str,
        top_k: int = 5,
    ) -> list[RetrievedChunk]: ...


class SaveDocumentPort(Protocol):
    """Puerto de salida para persistencia"""

    def exists_by_keys(self, payload: FetchDocumentPayload) -> bool: ...

    def save_document_with_embeddings(
        self, payload: SaveDocumentPayload
    ) -> SaveOutcome: ...


# HealthCheckPort/use-case no agregado debido a la tribialidad
