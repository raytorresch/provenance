from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.models.rag import Chunk, ChunkEmbedding, Document
from app.domain.entities import FetchDocumentPayload, SaveDocumentPayload, SaveOutcome


class StoreRepository:
    # Resolves idempotency against: adr_code, content_hash, chunking_strategy, model_name
    # adr_code doesn't exist - insert document, chunks and embeddings -> SaveOutcome.INSERTED
    # adr_code exists - content_hash doesn't match - replace all chunks (cascade deletes embeddings) -> SaveOutcome.REPLACED
    # adr_code exists - content_hash matches - chunking_strategy doesn't exist - add chunks and embeddings -> SaveOutcome.STRATEGY_ADDED
    # adr_code exists - content_hash matches - chunking_strategy exists - model_name doesn't exist - add embeddings only -> SaveOutcome.MODEL_ADDED
    # adr_code exists - content_hash matches - chunking_strategy exists - model_name exists - nothing to do
    #   (exists_by_keys already short-circuits this case before save is called)

    def __init__(self, session: Session) -> None:
        self._session = session

    def exists_by_keys(self, payload: FetchDocumentPayload) -> bool:
        stmt = (
            select(ChunkEmbedding.id)
            .select_from(Document)
            .join(Chunk, Chunk.document_id == Document.id)
            .join(ChunkEmbedding, ChunkEmbedding.chunk_id == Chunk.id)
            .where(Document.adr_code == payload.adr_code)
            .where(Document.content_hash == payload.content_hash)
            .where(Chunk.chunking_strategy == payload.chunking_strategy)
            .where(ChunkEmbedding.model_name == payload.model_name)
            .limit(1)
        )
        return self._session.execute(stmt).first() is not None

    def save_document_with_embeddings(self, payload: SaveDocumentPayload) -> SaveOutcome:
        """Only saves document, chunks and embeddings; validations are done in the use case.

        Raises on a payload/DB inconsistency (e.g. ordinals that don't match
        any existing chunk) instead of swallowing it as a falsy return.
        """

        document = self._session.execute(
            select(Document).where(Document.adr_code == payload.adr_code)
        ).scalar_one_or_none()

        if document is None:
            document = Document(
                adr_code=payload.adr_code,
                title=payload.title,
                source_url=payload.source_url,
                content_hash=payload.content_hash,
            )
            self._session.add(document)
            self._session.flush()  # need document.id for the chunks FK
            self._insert_chunks_with_embeddings(document.id, payload)
            self._session.commit()
            return SaveOutcome.INSERTED

        if document.content_hash != payload.content_hash:
            # Content changed: drop every chunk under every strategy for this
            # document (cascade deletes their embeddings) rather than only
            # the current payload's strategy. Chunks from another strategy
            # would otherwise keep answering retrieval with stale text.
            document.chunks.clear()
            document.title = payload.title
            document.source_url = payload.source_url
            document.content_hash = payload.content_hash
            self._session.flush()
            self._insert_chunks_with_embeddings(document.id, payload)
            self._session.commit()
            return SaveOutcome.REPLACED

        existing_chunks = (
            self._session.execute(
                select(Chunk)
                .where(Chunk.document_id == document.id)
                .where(Chunk.chunking_strategy == payload.chunking_strategy)
            )
            .scalars()
            .all()
        )

        if not existing_chunks:
            # Same content, new chunking strategy: add chunks + embeddings,
            # leaving chunks from other strategies untouched.
            self._insert_chunks_with_embeddings(document.id, payload)
            self._session.commit()
            return SaveOutcome.STRATEGY_ADDED

        # Same content, same strategy: chunks already exist, only the
        # embedding model is new. Attach embeddings to the existing chunk
        # rows by ordinal instead of duplicating chunks.
        chunk_id_by_ordinal = {chunk.ordinal: chunk.id for chunk in existing_chunks}
        unmatched_ordinals = [
            chunk_data.ordinal
            for chunk_data in payload.chunks
            if chunk_data.ordinal not in chunk_id_by_ordinal
        ]
        if unmatched_ordinals:
            raise ValueError(
                f"adr_code={payload.adr_code!r} chunking_strategy="
                f"{payload.chunking_strategy!r}: payload has chunks with "
                f"ordinals {unmatched_ordinals} that don't match any "
                "existing chunk"
            )

        embeddings = [
            ChunkEmbedding(
                chunk_id=chunk_id_by_ordinal[chunk_data.ordinal],
                model_name=payload.model_name,
                dimensions=len(vector),
                embedding=vector,
            )
            for chunk_data, vector in zip(
                payload.chunks, payload.embeddings, strict=True
            )
        ]
        self._session.add_all(embeddings)
        self._session.commit()
        return SaveOutcome.MODEL_ADDED

    def _insert_chunks_with_embeddings(
        self, document_id: int, payload: SaveDocumentPayload
    ) -> None:
        chunks = [
            Chunk(
                document_id=document_id,
                chunking_strategy=payload.chunking_strategy,
                ordinal=chunk_data.ordinal,
                heading_path=chunk_data.heading_path,
                content=chunk_data.content,
            )
            for chunk_data in payload.chunks
        ]
        self._session.add_all(chunks)
        self._session.flush()  # need chunk ids for the embeddings FK

        embeddings = [
            ChunkEmbedding(
                chunk_id=chunk.id,
                model_name=payload.model_name,
                dimensions=len(vector),
                embedding=vector,
            )
            for chunk, vector in zip(chunks, payload.embeddings, strict=True)
        ]
        self._session.add_all(embeddings)
