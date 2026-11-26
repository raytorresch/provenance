from __future__ import annotations

import argparse

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.adapters.outbound.embeddings.openai_compatible import OpenAICompatibleEmbedder
from app.adapters.outbound.persistence.repositories.retrieval_repository import (
    RetrievalRepository,
)
from app.application.retrieve import RetrieveChunksUseCase
from app.core.config import get_settings
from app.core.database import get_sqlalchemy_url
from app.domain.chunking import DEFAULT_MAX_CHARS
from app.domain.entities import RetrievedChunk


def print_top_chunks(chunks: list[RetrievedChunk]) -> None:
    if not chunks:
        print("(sin resultados)")
        return

    header = f"{'#':<3} {'adr_code':<12} {'similitud':<10} heading_path"
    print(header)
    print("-" * len(header))
    for rank, chunk in enumerate(chunks, start=1):
        print(f"{rank:<3} {chunk.adr_code:<12} {chunk.similarity:<10.4f} {chunk.heading_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retrieve the most similar ADR chunks for a question."
    )
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument(
        "--contextual-header",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Must match the strategy used at ingestion time, or nothing matches.",
    )
    args = parser.parse_args()

    settings = get_settings()
    embedder = OpenAICompatibleEmbedder.from_settings(settings)

    engine = create_engine(get_sqlalchemy_url())
    with Session(engine) as session:
        repository = RetrievalRepository(session)
        use_case = RetrieveChunksUseCase(
            embedder,
            repository,
            max_chars=args.max_chars,
            contextual_header=args.contextual_header,
        )
        chunks = use_case.execute(args.query, top_k=args.top_k)
    engine.dispose()

    print_top_chunks(chunks)


if __name__ == "__main__":
    main()
