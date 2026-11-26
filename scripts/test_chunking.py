import argparse
from pathlib import Path

from app.domain.chunking import DEFAULT_MAX_CHARS, chunk_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview chunking output for ADR markdown files.")
    parser.add_argument("adr_dir", nargs="?", default="docs/adr", type=Path)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    args = parser.parse_args()

    adr_paths = sorted(args.adr_dir.glob("*.md"))
    if not adr_paths:
        raise SystemExit(f"No .md files found in {args.adr_dir}")

    for path in adr_paths:
        chunks = chunk_markdown(path.read_text(encoding="utf-8"), max_chars=args.max_chars)
        print(f"\n== {path.name} ({len(chunks)} chunks) ==")
        for c in chunks:
            print(f"[{c.ordinal}] {c.heading_path} ({len(c.content)} chars)")


if __name__ == "__main__":
    main()
