"""Tests for bricks/stdlib/string_processing.py — 20 tests."""

from __future__ import annotations

import pytest

from bricks.stdlib.string_processing import (
    clean_whitespace,
    concatenate_strings,
    convert_case,
    count_words_chars,
    extract_emails,
    extract_markdown_fences,
    extract_regex_pattern,
    extract_urls,
    levenshtein_distance,
    pad_string,
    parse_date_string,
    redact_pii_patterns,
    remove_html_tags,
    replace_substring,
    reverse_string,
    split_by_delimiter,
    starts_ends_with,
    strip_punctuation,
    template_string_fill,
    truncate_string,
    truncate_text,
)


def test_template_string_fill_replaces_placeholders() -> None:
    assert template_string_fill("Hello {name}!", {"name": "World"})["result"] == "Hello World!"


def test_extract_regex_pattern_finds_all_matches() -> None:
    assert extract_regex_pattern("a1 b2 c3", r"\d")["result"] == ["1", "2", "3"]


def test_clean_whitespace_collapses_runs() -> None:
    assert clean_whitespace("  hello   world  ")["result"] == "hello world"


def test_truncate_text_adds_ellipsis() -> None:
    assert truncate_text("hello world", 8)["result"] == "hello..."


def test_truncate_text_no_cut_when_short() -> None:
    assert truncate_text("hi", 10)["result"] == "hi"


def test_concatenate_strings_with_separator() -> None:
    assert concatenate_strings(["a", "b", "c"], "-")["result"] == "a-b-c"


def test_split_by_delimiter_splits() -> None:
    assert split_by_delimiter("a,b,c", ",")["result"] == ["a", "b", "c"]


def test_redact_pii_patterns_removes_email() -> None:
    result = redact_pii_patterns("contact: user@example.com please")["result"]
    assert "[REDACTED_EMAIL]" in result


def test_parse_date_string_returns_iso() -> None:
    assert parse_date_string("25/12/2024", "%d/%m/%Y")["result"] == "2024-12-25"


def test_extract_urls_finds_urls() -> None:
    text = "Visit https://example.com and http://test.org"
    result = extract_urls(text)["result"]
    assert len(result) == 2


def test_remove_html_tags_strips_markup() -> None:
    assert remove_html_tags("<p>hello <b>world</b></p>")["result"] == "hello world"


def test_convert_case_upper() -> None:
    assert convert_case("hello", "upper")["result"] == "HELLO"


def test_convert_case_snake() -> None:
    assert convert_case("Hello World", "snake")["result"] == "hello_world"


def test_convert_case_unknown_raises() -> None:
    with pytest.raises(ValueError):
        convert_case("hi", "kebab")


def test_extract_emails_finds_addresses() -> None:
    result = extract_emails("send to a@b.com and x@y.org")["result"]
    assert len(result) == 2


def test_count_words_chars_correct() -> None:
    result = count_words_chars("hello world")["result"]
    assert result["words"] == 2 and result["chars"] == 11


def test_strip_punctuation_removes_dots() -> None:
    assert strip_punctuation("hello, world.")["result"] == "hello world"


def test_levenshtein_distance_kitten_sitting() -> None:
    assert levenshtein_distance("kitten", "sitting")["result"] == 3


def test_extract_markdown_fences_extracts_content() -> None:
    text = "```python\nprint('hi')\n```"
    assert "print" in extract_markdown_fences(text)["result"]


def test_pad_string_pads_left() -> None:
    assert pad_string("hi", 5)["result"] == "   hi"


def test_replace_substring_replaces_all() -> None:
    assert replace_substring("aaa", "a", "b")["result"] == "bbb"


def test_starts_ends_with_both_conditions() -> None:
    assert starts_ends_with("hello world", "hello", "world")["result"] is True


def test_reverse_string_reverses() -> None:
    assert reverse_string("abc")["result"] == "cba"


def test_truncate_string_short_text_unchanged() -> None:
    assert truncate_string("hello", 10)["result"] == "hello"


def test_truncate_string_truncates_long_text() -> None:
    assert truncate_string("hello world", 8)["result"] == "hello..."


def test_truncate_string_custom_suffix() -> None:
    assert truncate_string("hello world", 7, "~")["result"] == "hello ~"
