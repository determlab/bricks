"""Measurement bricks — 1 brick."""

from __future__ import annotations

import math
from typing import Any

from bricks.core.brick import brick


@brick(tags=["measurement", "pass-fail", "range"], category="measurement", destructive=False)
def measure(
    name: str,
    value: float,
    unit: str,
    min: float | None = None,
    max: float | None = None,
) -> dict[str, dict[str, Any]]:
    """Build one measurement row with a pass verdict. Returns {result: {name, value, unit, limits, pass}}.

    Args:
        name: Measurement name.
        value: Measured value.
        unit: Unit the value is expressed in (e.g. ``"V"``, ``"mm"``).
        min: Lower bound, inclusive (default None — no lower bound).
        max: Upper bound, inclusive (default None — no upper bound).

    Returns:
        dict with key ``result`` containing one measurement row: ``name``,
        ``value``, ``unit``, ``limits`` (only the bounds given; ``{}`` if
        neither was given), and ``pass`` (False if ``value`` is not finite,
        or falls outside a given bound; True otherwise).

    Raises:
        ValueError: If both bounds are given and min is above max.
    """
    if min is not None and max is not None and min > max:
        raise ValueError(f"min ({min}) must not be greater than max ({max})")

    limits: dict[str, float] = {}
    if min is not None:
        limits["min"] = min
    if max is not None:
        limits["max"] = max

    passed = math.isfinite(value)
    if passed and min is not None and value < min:
        passed = False
    if passed and max is not None and value > max:
        passed = False

    return {
        "result": {
            "name": name,
            "value": value,
            "unit": unit,
            "limits": limits,
            "pass": passed,
        }
    }
