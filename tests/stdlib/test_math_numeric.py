"""Tests for bricks/stdlib/math_numeric.py — 10 tests."""

from __future__ import annotations

import pytest

from bricks.stdlib.math_numeric import (
    absolute_value,
    ceil_value,
    clamp_value,
    divide,
    floor_value,
    max_value,
    min_value,
    modulo,
    percentage,
    power,
    round_number,
)


def test_divide_returns_quotient() -> None:
    assert divide(10.0, 4.0)["result"] == pytest.approx(2.5)


def test_divide_by_zero_raises() -> None:
    with pytest.raises(ZeroDivisionError):
        divide(5.0, 0.0)


def test_modulo_returns_remainder() -> None:
    assert modulo(10, 3)["result"] == 1


def test_absolute_value_negative() -> None:
    assert absolute_value(-7.5)["result"] == pytest.approx(7.5)


def test_min_value_returns_smaller() -> None:
    assert min_value(3.0, 7.0)["result"] == pytest.approx(3.0)


def test_max_value_returns_larger() -> None:
    assert max_value(3.0, 7.0)["result"] == pytest.approx(7.0)


def test_power_squares() -> None:
    assert power(3.0, 2.0)["result"] == pytest.approx(9.0)


def test_percentage_of_total() -> None:
    assert percentage(25.0, 200.0)["result"] == pytest.approx(12.5)


def test_clamp_value_within_range() -> None:
    assert clamp_value(15.0, 0.0, 10.0)["result"] == pytest.approx(10.0)


def test_ceil_and_floor() -> None:
    assert ceil_value(2.3)["result"] == 3
    assert floor_value(2.9)["result"] == 2


def test_round_number_to_integer() -> None:
    assert round_number(2.6)["result"] == 3.0


def test_round_number_decimal_places() -> None:
    assert round_number(3.14159, 2)["result"] == pytest.approx(3.14)


def test_round_number_negative() -> None:
    assert round_number(-1.5)["result"] == pytest.approx(-2.0)
