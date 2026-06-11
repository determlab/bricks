"""Tests for bricks/stdlib/encoding_security.py — 10 tests."""

from __future__ import annotations

import pytest

from bricks.stdlib.encoding_security import (
    base64_decode,
    base64_encode,
    compute_hash,
    escape_special_chars,
    generate_uuid,
    html_escape,
    html_unescape,
    mask_string,
    random_string,
    url_decode,
    url_encode,
)


def test_base64_encode_decode_roundtrip() -> None:
    encoded = base64_encode("hello world")["result"]
    assert base64_decode(encoded)["result"] == "hello world"


def test_compute_hash_sha256_length() -> None:
    result = compute_hash("test", "sha256")["result"]
    assert len(result) == 64  # sha256 hex digest is 64 chars


def test_compute_hash_unsupported_raises() -> None:
    with pytest.raises(ValueError):
        compute_hash("test", "rot13")


def test_url_encode_encodes_spaces() -> None:
    assert url_encode("hello world")["result"] == "hello%20world"


def test_url_decode_restores_spaces() -> None:
    assert url_decode("hello%20world")["result"] == "hello world"


def test_html_escape_encodes_angle_brackets() -> None:
    assert html_escape("<b>bold</b>")["result"] == "&lt;b&gt;bold&lt;/b&gt;"


def test_html_unescape_restores_entities() -> None:
    assert html_unescape("&lt;b&gt;")["result"] == "<b>"


def test_escape_special_chars_backslash_escapes() -> None:
    result = escape_special_chars("a.b*c", [".", "*"])["result"]
    assert result == r"a\.b\*c"


def test_generate_uuid_is_valid_format() -> None:
    result = generate_uuid()["result"]
    parts = result.split("-")
    assert len(parts) == 5


def test_random_string_correct_length() -> None:
    result = random_string(16, "alphanumeric")["result"]
    assert len(result) == 16


def test_random_string_unknown_charset_raises() -> None:
    with pytest.raises(ValueError):
        random_string(8, "emoji")


def test_mask_string_masks_all_but_last_four() -> None:
    assert mask_string("1234567890")["result"] == "******7890"


def test_mask_string_short_string_fully_masked() -> None:
    assert mask_string("abc", 4)["result"] == "***"


def test_mask_string_custom_mask_char() -> None:
    assert mask_string("secret123", 3, "#")["result"] == "######123"
