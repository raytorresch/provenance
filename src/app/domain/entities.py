from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True)
class ChunkData:
    ordinal: int
    heading_path: str
    content: str


@dataclass(frozen=True)
class DocumentInput:
    adr_code: str
    title: str
    source_url: str
    raw_markdown: str


@dataclass(frozen=True)
class RetrievedChunk:
    adr_code: str
    title: str
    heading_path: str
    content: str
    similarity: float


@dataclass(frozen=True)
class SaveDocumentPayload:
    adr_code: str
    title: str
    source_url: str
    content_hash: str
    chunking_strategy: str
    chunks: list[ChunkData]
    embeddings: list[list[float]]
    model_name: str


@dataclass(frozen=True)
class FetchDocumentPayload:
    adr_code: str
    content_hash: str
    chunking_strategy: str
    model_name: str


class SaveOutcome(StrEnum):
    """Which idempotency case save_document_with_embeddings actually took,
    so a caller (e.g. a CLI ingesting a batch of ADRs) can report what
    happened to each document instead of a flat boolean."""

    INSERTED = "inserted"
    REPLACED = "replaced"
    STRATEGY_ADDED = "strategy_added"
    MODEL_ADDED = "model_added"
