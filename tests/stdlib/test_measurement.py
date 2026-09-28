"""Tests for bricks/stdlib/measurement.py — 1 brick."""

from __future__ import annotations

import math

import pytest

from bricks.stdlib.measurement import measure


def test_measure_in_range_passes() -> None:
    row = measure("vout", 4.98, "V", min=4.9, max=5.1)["result"]
    assert row == {
        "name": "vout",
        "value": 4.98,
        "unit": "V",
        "limits": {"min": 4.9, "max": 5.1},
        "pass": True,
    }


def test_measure_below_min_fails() -> None:
    row = measure("vout", 4.5, "V", min=4.9, max=5.1)["result"]
    assert row["pass"] is False
    assert row["limits"] == {"min": 4.9, "max": 5.1}


def test_measure_above_max_fails() -> None:
    row = measure("vout", 5.5, "V", min=4.9, max=5.1)["result"]
    assert row["pass"] is False


def test_measure_bounds_are_inclusive() -> None:
    assert measure("vout", 4.9, "V", min=4.9, max=5.1)["result"]["pass"] is True
    assert measure("vout", 5.1, "V", min=4.9, max=5.1)["result"]["pass"] is True


def test_measure_no_bounds_passes_with_empty_limits() -> None:
    row = measure("vout", 4.98, "V")["result"]
    assert row["limits"] == {}
    assert row["pass"] is True


def test_measure_nan_value_fails() -> None:
    row = measure("vout", math.nan, "V")["result"]
    assert row["pass"] is False


def test_measure_inf_value_fails() -> None:
    row = measure("vout", math.inf, "V", min=4.9, max=5.1)["result"]
    assert row["pass"] is False


def test_measure_never_raises_on_failing_value() -> None:
    # Out of bounds and non-finite values return pass: false, they never raise.
    measure("vout", -1.0, "V", min=0.0, max=1.0)
    measure("vout", math.nan, "V", min=0.0, max=1.0)


def test_measure_min_greater_than_max_raises() -> None:
    with pytest.raises(ValueError, match=r"5\.1.*4\.9"):
        measure("vout", 5.0, "V", min=5.1, max=4.9)


def test_measure_only_min_bound() -> None:
    row = measure("vout", 4.98, "V", min=4.9)["result"]
    assert row["limits"] == {"min": 4.9}
    assert row["pass"] is True
