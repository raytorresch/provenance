from dataclasses import dataclass


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