from pathlib import Path
from typing import Protocol

from app.domain.entities import ChunkData, RetrievedChunk


class DocumentExtractorPort(Protocol):
  """Puerto de salida para extraer texto Markdown desde cualquier origen."""

  def extract_markdown(self, source: Path) -> str: ...


class EmbeddingProviderPort(Protocol):
  """Puerto de salida para generar vectores sin acoplarse a Gemini/OpenAI/Local."""

  @property
  def model_name(self) -> str: ...

  def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


class DocumentRepositoryPort(Protocol):
  """Puerto de salida para persistencia y búsqueda vectorial."""

  def exists_by_hash(self, content_hash: str) -> bool: ...

  def save_document_with_embeddings(
      self,
      adr_code: str,
      title: str,
      source_url: str,
      content_hash: str,
      chunks: list[ChunkData],
      embeddings: list[list[float]],
      model_name: str,
  ) -> int: ...

  def search_similar(
      self,
      query_embedding: list[float],
      model_name: str,
      top_k: int = 5,
  ) -> list[RetrievedChunk]: ...