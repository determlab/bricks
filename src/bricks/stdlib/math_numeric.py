"""Math / Numeric bricks — 10 new operations.

The 5 original math bricks (add, subtract, multiply, round_value, format_result)
live in benchmark/showcase/bricks/math_bricks.py and are not repeated here.
"""

from __future__ import annotations

import math

from bricks.core.brick import brick


@brick(tags=["math", "arithmetic"], category="math", destructive=False)
def divide(a: float, b: float) -> dict[str, float]:
    """Divide a by b. Returns {result: quotient}.

    Args:
        a: Dividend.
        b: Divisor (must not be zero).

    Returns:
        dict with key ``result`` containing the quotient.

    Raises:
        ZeroDivisionError: If b is zero.
    """
    if b == 0:
        raise ZeroDivisionError("Division by zero: b must not be 0")
    return {"result": a / b}


@brick(tags=["math", "arithmetic"], category="math", destructive=False)
def modulo(a: float, b: float) -> dict[str, float]:
    """Compute a modulo b. Returns {result: remainder}.

    Args:
        a: Dividend.
        b: Divisor (must not be zero).

    Returns:
        dict with key ``result`` containing the remainder.

    Raises:
        ZeroDivisionError: If b is zero.
    """
    if b == 0:
        raise ZeroDivisionError("Modulo by zero: b must not be 0")
    return {"result": a % b}


@brick(tags=["math", "arithmetic"], category="math", destructive=False)
def absolute_value(value: float) -> dict[str, float]:
    """Return the absolute value of a number. Returns {result: absolute}.

    Args:
        value: Input number.

    Returns:
        dict with key ``result`` containing the non-negative value.
    """
    return {"result": abs(value)}


@brick(tags=["math", "comparison"], category="math", destructive=False)
def min_value(a: float, b: float) -> dict[str, float]:
    """Return the smaller of two numbers. Returns {result: minimum}.

    Args:
        a: First number.
        b: Second number.

    Returns:
        dict with key ``result`` containing the minimum.
    """
    return {"result": min(a, b)}


@brick(tags=["math", "comparison"], category="math", destructive=False)
def max_value(a: float, b: float) -> dict[str, float]:
    """Return the larger of two numbers. Returns {result: maximum}.

    Args:
        a: First number.
        b: Second number.

    Returns:
        dict with key ``result`` containing the maximum.
    """
    return {"result": max(a, b)}


@brick(tags=["math", "arithmetic"], category="math", destructive=False)
def power(base: float, exponent: float) -> dict[str, float]:
    """Raise base to the power of exponent. Returns {result: power}.

    Args:
        base: The base number.
        exponent: The exponent.

    Returns:
        dict with key ``result`` containing base ** exponent.
    """
    return {"result": base**exponent}


@brick(tags=["math", "percentage"], category="math", destructive=False)
def percentage(value: float, total: float) -> dict[str, float]:
    """Compute (value / total) * 100. Returns {result: percentage}.

    Args:
        value: The part value.
        total: The whole value (must not be zero).

    Returns:
        dict with key ``result`` containing the percentage.

    Raises:
        ZeroDivisionError: If total is zero.
    """
    if total == 0:
        raise ZeroDivisionError("total must not be zero")
    return {"result": (value / total) * 100}


@brick(tags=["math", "range"], category="math", destructive=False)
def clamp_value(value: float, minimum: float, maximum: float) -> dict[str, float]:
    """Clamp value to [minimum, maximum]. Returns {result: clamped}.

    Args:
        value: The input number.
        minimum: Lower bound (inclusive).
        maximum: Upper bound (inclusive).

    Returns:
        dict with key ``result`` containing the clamped value.
    """
    return {"result": max(minimum, min(maximum, value))}


@brick(tags=["math", "rounding"], category="math", destructive=False)
def ceil_value(value: float) -> dict[str, int]:
    """Round value up to nearest integer. Returns {result: ceiling}.

    Args:
        value: Input number.

    Returns:
        dict with key ``result`` containing the ceiling integer.
    """
    return {"result": math.ceil(value)}


@brick(tags=["math", "rounding"], category="math", destructive=False)
def floor_value(value: float) -> dict[str, int]:
    """Round value down to nearest integer. Returns {result: floor}.

    Args:
        value: Input number.

    Returns:
        dict with key ``result`` containing the floor integer.
    """
    return {"result": math.floor(value)}


@brick(tags=["math", "rounding"], category="math", destructive=False)
def round_number(value: float, decimal_places: int = 0) -> dict[str, float]:
    """Round a number to the specified number of decimal places. Returns {result: rounded}.

    Args:
        value: Input number.
        decimal_places: Number of decimal places (default 0 rounds to integer).

    Returns:
        dict with key ``result`` containing the rounded float.
    """
    return {"result": round(value, decimal_places)}
