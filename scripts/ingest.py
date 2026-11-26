from __future__ import annotations

import argparse
import re
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.adapters.outbound.embeddings.openai_compatible import OpenAICompatibleEmbedder
from app.adapters.outbound.extractors.markdown import MarkdownFileExtractor
from app.adapters.outbound.persistence.repositories.store_repository import (
    StoreRepository,
)
from app.application.ingest_adr import IngestAdrUseCase
from app.core.config import get_settings
from app.core.database import get_sqlalchemy_url
from app.domain.chunking import DEFAULT_MAX_CHARS
from app.domain.entities import DocumentInput

_ADR_FILENAME_RE = re.compile(r"^(\d+)-(.+)$")


def _adr_code_for(path: Path) -> str:
    match = _ADR_FILENAME_RE.match(path.stem)
    number = match.group(1) if match else path.stem
    return f"ADR-{number}"


def _title_for(path: Path, raw_markdown: str) -> str:
    for line in raw_markdown.splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    match = _ADR_FILENAME_RE.match(path.stem)
    slug = match.group(2) if match else path.stem
    return slug.replace("-", " ").title()


def _source_url_for(path: Path, base_url: str | None) -> str:
    if base_url is None:
        return str(path)
    return f"{base_url.rstrip('/')}/{path.name}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest ADR markdown files into the RAG store."
    )
    parser.add_argument("adr_dir", nargs="?", default=Path("docs/adr"), type=Path)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument(
        "--base-url",
        default=None,
        help=(
            "Public URL prefix used to build each ADR's source_url, e.g. "
            "https://github.com/org/repo/blob/main/adr. Without it, "
            "source_url falls back to the local file path."
        ),
    )
    parser.add_argument(
        "--contextual-header",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Prefix each chunk's embedded text with its heading path.",
    )
    args = parser.parse_args()

    adr_paths = sorted(args.adr_dir.glob("*.md"))
    if not adr_paths:
        raise SystemExit(f"No .md files found in {args.adr_dir}")

    settings = get_settings()
    extractor = MarkdownFileExtractor()
    embedder = OpenAICompatibleEmbedder.from_settings(settings)

    failures = 0
    engine = create_engine(get_sqlalchemy_url())
    with Session(engine) as session:
        repository = StoreRepository(session)
        use_case = IngestAdrUseCase(
            repository=repository,
            embedder=embedder,
            max_chars=args.max_chars,
            contextual_header=args.contextual_header,
        )

        for path in adr_paths:
            raw_markdown = extractor.extract_markdown(path)
            doc = DocumentInput(
                adr_code=_adr_code_for(path),
                title=_title_for(path, raw_markdown),
                source_url=_source_url_for(path, args.base_url),
                raw_markdown=raw_markdown,
            )
            try:
                outcome = use_case.execute(doc)
            except Exception as exc:  # noqa: BLE001 - one bad ADR must not abort the batch
                print(f"{doc.adr_code}: ERROR - {exc}")
                failures += 1
                continue
            print(f"{doc.adr_code}: {outcome.value}")

    engine.dispose()

    if failures:
        raise SystemExit(f"{failures} of {len(adr_paths)} ADR(s) failed to ingest.")


if __name__ == "__main__":
    main()
