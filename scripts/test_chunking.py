from pathlib import Path

from app.domain.chunking import chunk_markdown

adr_text = Path("scripts/sample_adr.md").read_text(encoding="utf-8")
chunks = chunk_markdown(adr_text)

for c in chunks:
    print(f"[{c.ordinal}] {c.heading_path} ({len(c.content)} chars)")
