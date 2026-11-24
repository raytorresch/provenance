import hashlib

from app.domain.chunking import chunk_markdown
from app.domain.entities import DocumentInput
from app.domain.ports import DocumentRepositoryPort, EmbeddingProviderPort


class IngestAdrUseCase:

  def __init__(
      self,
      repository: DocumentRepositoryPort,
      embedder: EmbeddingProviderPort,
  ) -> None:
    self._repo = repository
    self._embedder = embedder

  def execute(self, doc: DocumentInput) -> bool:
    """Ingesta un ADR de forma idempotente. Retorna True si se insertó, False si ya existía."""
    content_hash = hashlib.sha256(
        doc.raw_markdown.encode("utf-8")
    ).hexdigest()

    # 1. Idempotencia: no gastamos llamadas de embedding
    if self._repo.exists_by_hash(content_hash):
      return False

    # 2. Dominio: fragmentar Markdown
    chunks = chunk_markdown(doc.raw_markdown)
    if not chunks:
      return False

    # 3. Contextual Header Injection antes de embeber
    texts_to_embed = [f"{c.heading_path}\n\n{c.content}" for c in chunks]

    # 4. Generar vectores
    vectors = self._embedder.embed_texts(texts_to_embed)

    # 5. Persistir
    self._repo.save_document_with_embeddings(
        adr_code=doc.adr_code,
        title=doc.title,
        source_url=doc.source_url,
        content_hash=content_hash,
        chunks=chunks,
        embeddings=vectors,
        model_name=self._embedder.model_name,
    )
    return True