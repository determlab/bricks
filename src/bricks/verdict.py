"""Derive a pass/fail/error verdict for one blueprint run against one unit.

Record.md §2: the verdict is derived, never set by hand. ``derive_verdict`` is
pure — it only reads ``ExecutionResult.steps`` for rows a ``measure`` step
produced — because a run that raises before returning an ``ExecutionResult``
(a failed guard, or any other :class:`~bricks.core.exceptions.BrickError`)
carries no steps to read. Those two cases are turned into a :class:`Verdict`
by the caller (``bricks.cli.main``), not by this module.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from bricks.core.models import ExecutionResult

_MEASURE_BRICK = "measure"


class VerdictStatus(str, Enum):
    """The three values a run's verdict can take."""

    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"


class Verdict(BaseModel):
    """The outcome of one blueprint run against one unit.

    ``measurements`` is every ``measure`` step's output row, tagged with its
    step name — empty when the run carried no ``measure`` step, or ended
    before any ``ExecutionResult`` existed (a failed guard, or another
    ``BrickError``). ``reason`` is a one-line, human-readable explanation for
    a ``fail`` or ``error`` verdict; empty on ``pass``.
    """

    status: VerdictStatus
    measurements: list[dict[str, Any]] = Field(default_factory=list)
    reason: str = ""


def _measurements(result: ExecutionResult) -> list[dict[str, Any]]:
    """Every ``measure`` step's output row in *result*, tagged with its step name."""
    rows: list[dict[str, Any]] = []
    for step in result.steps:
        if step.brick_name != _MEASURE_BRICK:
            continue
        row = step.outputs.get("result")
        if not isinstance(row, dict):
            continue
        rows.append({"step": step.step_name, **row})
    return rows


def _fail_reason(row: dict[str, Any]) -> str:
    """A one-line reason a failing measurement row failed, e.g. ``vout 4.7 V not in [4.9, 5.1]``."""
    limits = row.get("limits") or {}
    if "min" in limits and "max" in limits:
        bound = f"not in [{limits['min']}, {limits['max']}]"
    elif "min" in limits:
        bound = f"below min {limits['min']}"
    elif "max" in limits:
        bound = f"above max {limits['max']}"
    else:
        bound = "not finite"
    return f"{row.get('name')} {row.get('value')} {row.get('unit')} {bound}"


def derive_verdict(result: ExecutionResult) -> Verdict:
    """Derive the verdict for a run that completed without raising.

    ``fail`` if any ``measure`` step's row has ``pass: false``; otherwise
    ``pass``. Never returns ``error`` — a run that ends in a ``BrickError``
    other than a failed guard never reaches this function; see the module
    docstring.
    """
    measurements = _measurements(result)
    failing = [row for row in measurements if row.get("pass") is False]
    if failing:
        return Verdict(status=VerdictStatus.FAIL, measurements=measurements, reason=_fail_reason(failing[0]))
    return Verdict(status=VerdictStatus.PASS, measurements=measurements)
