from __future__ import annotations

from app.domain.chunking import (
    _split_long_section,
    build_chunking_strategy,
    chunk_markdown,
)


def test_empty_document_produces_no_chunks() -> None:
    assert chunk_markdown("") == []


def test_whitespace_only_document_produces_no_chunks() -> None:
    assert chunk_markdown("   \n\n   \n") == []


def test_content_before_any_heading_is_preamble() -> None:
    chunks = chunk_markdown("Just a paragraph of text.")

    assert len(chunks) == 1
    assert chunks[0].ordinal == 0
    assert chunks[0].heading_path == "Preamble"
    assert chunks[0].content == "Just a paragraph of text."


def test_single_heading_assigns_its_title_as_path() -> None:
    chunks = chunk_markdown("# Title\nSome content here.")

    assert len(chunks) == 1
    assert chunks[0].heading_path == "Title"
    assert chunks[0].content == "Some content here."


def test_content_is_attributed_to_the_heading_that_precedes_it() -> None:
    text = "# T1\nIntro text.\n## S1\nBody text."

    chunks = chunk_markdown(text)

    assert [(c.heading_path, c.content) for c in chunks] == [
        ("T1", "Intro text."),
        ("T1 > S1", "Body text."),
    ]


def test_heading_path_nests_h1_h2_h3() -> None:
    text = "# A\n## B\n### C\nDeep content."

    chunks = chunk_markdown(text)

    assert chunks[0].heading_path == "A > B > C"
    assert chunks[0].content == "Deep content."


def test_new_h1_resets_h2_and_h3() -> None:
    text = "# A\n## B\n### C\nDeep content.\n# D\nTop content again."

    chunks = chunk_markdown(text)

    assert [(c.heading_path, c.content) for c in chunks] == [
        ("A > B > C", "Deep content."),
        ("D", "Top content again."),
    ]


def test_new_h2_resets_h3_but_keeps_h1() -> None:
    text = "# A\n## B\n### C\nX\n## D\nY"

    chunks = chunk_markdown(text)

    assert [(c.heading_path, c.content) for c in chunks] == [
        ("A > B > C", "X"),
        ("A > D", "Y"),
    ]


def test_heading_like_line_inside_code_block_is_not_treated_as_heading() -> None:
    text = "# T1\n```\n# not a heading\n```\nAfter code."

    chunks = chunk_markdown(text)

    assert len(chunks) == 1
    assert chunks[0].heading_path == "T1"
    assert chunks[0].content == "```\n# not a heading\n```\nAfter code."


def test_ordinal_is_a_continuous_counter_across_sections_and_sub_chunks() -> None:
    long_section = "# T\n" + "X" * 10 + "\n\n" + "Y" * 10 + "\n\n## S\nShort tail."

    chunks = chunk_markdown(long_section, max_chars=15)

    assert [c.ordinal for c in chunks] == [0, 1, 2]
    assert chunks[0].heading_path == "T"
    assert chunks[0].content == "X" * 10
    assert chunks[1].heading_path == "T"
    assert chunks[1].content == "Y" * 10
    assert chunks[2].heading_path == "T > S"
    assert chunks[2].content == "Short tail."


def test_split_long_section_returns_text_unchanged_when_within_limit() -> None:
    assert _split_long_section("short", max_chars=100) == ["short"]


def test_split_long_section_splits_on_paragraph_boundaries() -> None:
    text = "A" * 10 + "\n\n" + "B" * 10

    parts = _split_long_section(text, max_chars=15)

    assert parts == ["A" * 10, "B" * 10]


def test_split_long_section_overlaps_small_trailing_block_into_next_part() -> None:
    text = "AAAAA\n\nBBBBB\n\nCCCCC"

    parts = _split_long_section(text, max_chars=15)

    assert parts == ["AAAAA\n\nBBBBB", "BBBBB\n\nCCCCC"]


def test_split_long_section_keeps_code_block_atomic_despite_internal_blank_line() -> (
    None
):
    text = "```\nline1\n\nline2\n```"

    parts = _split_long_section(text, max_chars=1)

    assert parts == [text]


def test_trailing_colon_is_stripped_from_heading_path() -> None:
    chunks = chunk_markdown("# T\n## Context:\nSome text.")

    assert chunks[0].heading_path == "T > Context"


def test_build_chunking_strategy_encodes_max_chars_and_header_flag() -> None:
    assert (
        build_chunking_strategy(1500, contextual_header=True)
        == "by_heading_v1:max=1500:hdr=1"
    )
    assert (
        build_chunking_strategy(1500, contextual_header=False)
        == "by_heading_v1:max=1500:hdr=0"
    )


def test_build_chunking_strategy_changes_label_when_max_chars_changes() -> None:
    small = build_chunking_strategy(500, contextual_header=True)
    large = build_chunking_strategy(1500, contextual_header=True)

    assert small != large
