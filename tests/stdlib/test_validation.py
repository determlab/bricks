"""Tests for bricks/stdlib/validation.py — 10 tests."""

from __future__ import annotations

import pytest

from bricks.stdlib.validation import (
    compare_values,
    has_required_keys,
    is_email_valid,
    is_in_range,
    is_iso_date,
    is_not_empty,
    is_numeric_string,
    is_phone_valid,
    is_url_valid,
    matches_pattern,
)


def test_is_email_valid_accepts_valid() -> None:
    assert is_email_valid("user@example.com")["result"] is True


def test_is_email_valid_rejects_invalid() -> None:
    assert is_email_valid("not-an-email")["result"] is False


def test_is_url_valid_accepts_https() -> None:
    assert is_url_valid("https://example.com")["result"] is True


def test_is_url_valid_rejects_bare_string() -> None:
    assert is_url_valid("example.com")["result"] is False


def test_is_phone_valid_us_number() -> None:
    assert is_phone_valid("555-123-4567")["result"] is True


def test_is_not_empty_rejects_empty_string() -> None:
    assert is_not_empty("")["result"] is False


def test_is_in_range_within_bounds() -> None:
    assert is_in_range(5.0, 1.0, 10.0)["result"] is True


def test_matches_pattern_full_match() -> None:
    assert matches_pattern("abc123", r"[a-z]+\d+")["result"] is True


def test_has_required_keys_all_present() -> None:
    assert has_required_keys({"a": 1, "b": 2}, ["a", "b"])["result"] is True


def test_is_numeric_string_valid_float() -> None:
    assert is_numeric_string("3.14")["result"] is True


def test_is_iso_date_valid_date() -> None:
    assert is_iso_date("2024-01-15")["result"] is True


def test_compare_values_greater_than() -> None:
    assert compare_values(10, 5, "gt")["result"] is True


def test_compare_values_unknown_operator_raises() -> None:
    with pytest.raises(ValueError):
        compare_values(1, 2, "??")
