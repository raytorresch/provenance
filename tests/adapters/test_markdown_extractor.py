from __future__ import annotations

from pathlib import Path

import pytest

from app.adapters.outbound.extractors.markdown import MarkdownFileExtractor


def test_extract_markdown_returns_file_contents(tmp_path: Path) -> None:
    source = tmp_path / "doc.md"
    source.write_text("# Title\nSome café ☕ content.", encoding="utf-8")

    result = MarkdownFileExtractor().extract_markdown(source)

    assert result == "# Title\nSome café ☕ content."


def test_extract_markdown_raises_file_not_found_for_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.md"

    with pytest.raises(FileNotFoundError, match=str(missing)):
        MarkdownFileExtractor().extract_markdown(missing)
