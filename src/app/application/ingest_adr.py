import hashlib
from enum import StrEnum

from app.domain.chunking import (
    DEFAULT_MAX_CHARS,
    build_chunking_strategy,
    chunk_markdown,
)
from app.domain.entities import (
    DocumentInput,
    FetchDocumentPayload,
    SaveDocumentPayload,
    SaveOutcome,
)
from app.domain.ports import EmbeddingProviderPort, SaveDocumentPort


class IngestOutcome(StrEnum):
    """Early-exit outcomes that never reach the repository. A successful
    save instead returns the repository's own SaveOutcome (INSERTED,
    REPLACED, STRATEGY_ADDED, MODEL_ADDED) so callers see exactly what
    happened, not a generic "saved"."""

    ALREADY_EXISTS = "already_exists"
    NO_CONTENT = "no_content"


class IngestAdrUseCase:
    def __init__(
        self,
        repository: SaveDocumentPort,
        embedder: EmbeddingProviderPort,
        max_chars: int = DEFAULT_MAX_CHARS,
        contextual_header: bool = True,
    ) -> None:
        self._repo = repository
        self._embedder = embedder
        self._max_chars = max_chars
        self._contextual_header = contextual_header

    def execute(self, doc: DocumentInput) -> IngestOutcome | SaveOutcome:
        """Ingesta un ADR de forma idempotente."""
        content_hash = hashlib.sha256(doc.raw_markdown.encode("utf-8")).hexdigest()
        strategy = build_chunking_strategy(
            max_chars=self._max_chars, contextual_header=self._contextual_header
        )

        fetch_payload = FetchDocumentPayload(
            adr_code=doc.adr_code,
            content_hash=content_hash,
            chunking_strategy=strategy,
            model_name=self._embedder.model_name,
        )

        # 1. Idempotencia: no gastamos llamadas de embedding
        if self._repo.exists_by_keys(fetch_payload):
            return IngestOutcome.ALREADY_EXISTS

        # 2. Dominio: fragmentar Markdown
        chunks = chunk_markdown(doc.raw_markdown, max_chars=self._max_chars)
        if not chunks:
            return IngestOutcome.NO_CONTENT

        # 3. Contextual Header Injection antes de embeber (parte de `strategy`)
        if self._contextual_header:
            texts_to_embed = [f"{c.heading_path}\n\n{c.content}" for c in chunks]
        else:
            texts_to_embed = [c.content for c in chunks]

        # 4. Generar vectores
        vectors = self._embedder.embed_texts(texts_to_embed)
        if len(vectors) != len(chunks):
            # Catch this here, before touching the repository/session. The
            # repository's zip(strict=True) would also catch it, but only
            # after document/chunk rows are already flushed.
            raise ValueError(
                f"embedder returned {len(vectors)} vectors for "
                f"{len(chunks)} chunks (adr_code={doc.adr_code!r})"
            )

        # 5. Persistir; un fallo se propaga como excepción, no como False.
        save_payload = SaveDocumentPayload(
            adr_code=doc.adr_code,
            title=doc.title,
            source_url=doc.source_url,
            content_hash=content_hash,
            chunking_strategy=strategy,
            chunks=chunks,
            embeddings=vectors,
            model_name=self._embedder.model_name,
        )
        return self._repo.save_document_with_embeddings(save_payload)
