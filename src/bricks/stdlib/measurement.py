"""Measurement bricks — 1 brick."""

from __future__ import annotations

import math
from typing import Any

from bricks.core.brick import brick


@brick(tags=["measurement", "test", "verdict"], category="measurement", destructive=False)
def measure(
    name: str,
    value: float,
    unit: str,
    min: float | None = None,
    max: float | None = None,
) -> dict[str, dict[str, Any]]:
    """Record one measurement with a pass flag. Returns {result: {name, value, unit, limits, pass}}.

    Args:
        name: Measurement name (e.g. ``"vout"``).
        value: Measured value.
        unit: Unit string (e.g. ``"V"``), carried through unchanged.
        min: Lower bound, inclusive. Omit for no lower bound.
        max: Upper bound, inclusive. Omit for no upper bound.

    Returns:
        dict with key ``result`` containing ``name``, ``value``, ``unit``,
        ``limits`` (only the bounds given, so ``{}`` when neither is given)
        and ``pass`` (whether ``value`` satisfies every given bound; always
        False when ``value`` is not finite, e.g. NaN or infinity).

    Raises:
        ValueError: If both bounds are given and ``min`` is greater than ``max``.
    """
    if min is not None and max is not None and min > max:
        raise ValueError(f"min must not exceed max: min={min}, max={max}")

    limits: dict[str, float] = {}
    if min is not None:
        limits["min"] = min
    if max is not None:
        limits["max"] = max

    if not math.isfinite(value):
        passed = False
    else:
        passed = (min is None or value >= min) and (max is None or value <= max)

    return {
        "result": {
            "name": name,
            "value": value,
            "unit": unit,
            "limits": limits,
            "pass": passed,
        }
    }
