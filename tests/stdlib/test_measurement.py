"""Tests for bricks/stdlib/measurement.py — 1 brick."""

from __future__ import annotations

import math

import pytest

from bricks.stdlib.measurement import measure


def test_in_range_passes() -> None:
    row = measure("vout", 4.98, "V", min=4.9, max=5.1)["result"]
    assert row == {
        "name": "vout",
        "value": 4.98,
        "unit": "V",
        "limits": {"min": 4.9, "max": 5.1},
        "pass": True,
    }


def test_below_min_fails() -> None:
    row = measure("vout", 4.5, "V", min=4.9, max=5.1)["result"]
    assert row["pass"] is False
    assert row["limits"] == {"min": 4.9, "max": 5.1}


def test_above_max_fails() -> None:
    row = measure("vout", 5.5, "V", min=4.9, max=5.1)["result"]
    assert row["pass"] is False


def test_bound_is_inclusive() -> None:
    assert measure("vout", 4.9, "V", min=4.9, max=5.1)["result"]["pass"] is True
    assert measure("vout", 5.1, "V", min=4.9, max=5.1)["result"]["pass"] is True


def test_no_bounds_passes_with_empty_limits() -> None:
    row = measure("vout", 4.98, "V")["result"]
    assert row["limits"] == {}
    assert row["pass"] is True


def test_only_min_given() -> None:
    row = measure("vout", 4.98, "V", min=4.9)["result"]
    assert row["limits"] == {"min": 4.9}
    assert row["pass"] is True
    assert measure("vout", 4.5, "V", min=4.9)["result"]["pass"] is False


def test_only_max_given() -> None:
    row = measure("vout", 4.98, "V", max=5.1)["result"]
    assert row["limits"] == {"max": 5.1}
    assert row["pass"] is True
    assert measure("vout", 5.5, "V", max=5.1)["result"]["pass"] is False


def test_nan_value_fails_even_with_no_bounds() -> None:
    row = measure("vout", math.nan, "V")["result"]
    assert row["pass"] is False


def test_infinite_value_fails() -> None:
    assert measure("vout", math.inf, "V")["result"]["pass"] is False
    assert measure("vout", -math.inf, "V", min=0.0, max=10.0)["result"]["pass"] is False


def test_min_greater_than_max_raises() -> None:
    with pytest.raises(ValueError, match=r"5\.1.*4\.9|4\.9.*5\.1"):
        measure("vout", 5.0, "V", min=5.1, max=4.9)


def test_never_raises_on_a_failing_value() -> None:
    """A value outside bounds returns pass: false; it does not raise."""
    row = measure("vout", 100.0, "V", min=0.0, max=10.0)["result"]
    assert row["pass"] is False
