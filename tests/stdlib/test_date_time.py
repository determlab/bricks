"""Tests for bricks/stdlib/date_time.py — 10 tests."""

from __future__ import annotations

from bricks.stdlib.date_time import (
    add_days,
    add_hours,
    convert_timezone,
    date_diff,
    date_range,
    days_until,
    extract_date_parts,
    format_date,
    is_business_day,
    now_timestamp,
    parse_date,
)


def test_parse_date_returns_iso() -> None:
    assert parse_date("25/12/2024", "%d/%m/%Y")["result"] == "2024-12-25"


def test_format_date_custom_format() -> None:
    assert format_date("2024-01-05", "%d %B %Y")["result"] == "05 January 2024"


def test_date_diff_positive_days() -> None:
    assert date_diff("2024-01-10", "2024-01-05")["result"] == 5


def test_add_days_forward() -> None:
    assert add_days("2024-01-01", 7)["result"] == "2024-01-08"


def test_add_hours_forward() -> None:
    assert add_hours("2024-01-01T12:00:00", 3)["result"] == "2024-01-01T15:00:00"


def test_now_timestamp_is_string() -> None:
    result = now_timestamp()["result"]
    assert isinstance(result, str) and "T" in result


def test_convert_timezone_utc_to_eastern() -> None:
    result = convert_timezone("2024-06-15T12:00:00", "UTC", "America/New_York")["result"]
    assert result == "2024-06-15T08:00:00"


def test_extract_date_parts_monday() -> None:
    # 2024-01-01 is a Monday (weekday=0)
    parts = extract_date_parts("2024-01-01")["result"]
    assert parts["year"] == 2024 and parts["weekday"] == 0


def test_is_business_day_friday_true() -> None:
    # 2024-01-05 is a Friday
    assert is_business_day("2024-01-05")["result"] is True


def test_date_range_generates_dates() -> None:
    result = date_range("2024-01-01", "2024-01-04")["result"]
    assert result == ["2024-01-01", "2024-01-02", "2024-01-03"]


def test_days_until_past_date_is_negative() -> None:
    result = days_until("2020-01-01")["result"]
    assert result < 0


def test_days_until_far_future_is_positive() -> None:
    result = days_until("2099-12-31")["result"]
    assert result > 0
