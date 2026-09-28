"""Pass/fail/error verdict for one blueprint run (#49).

``bricks run`` reports a verdict for a test blueprint, never set by hand
(ops `record.md` §2): it is derived from what the run actually did.

- ``fail`` — any ``measure`` step returned ``pass: false``, or a guard step
  stopped the run (``GuardFailedError``).
- ``error`` — any other ``BrickError`` ended the run.
- ``pass`` — otherwise.

:func:`derive_verdict` is pure and only reads ``ExecutionResult.steps`` where
``brick_name == "measure"``: no I/O, clock or random. A guard failure or any
other ``BrickError`` stops :meth:`BlueprintEngine.run` before it returns an
``ExecutionResult`` at all, so those two verdicts are built directly from the
exception by :func:`verdict_for_guard_failure` / :func:`verdict_for_error`
instead of going through :func:`derive_verdict`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from bricks.core.exceptions import BrickError, GuardFailedError
from bricks.core.models import ExecutionResult

VerdictStatus = Literal["pass", "fail", "error"]


@dataclass(frozen=True)
class Verdict:
    """The verdict for one blueprint run.

    Attributes:
        status: ``"pass"``, ``"fail"`` or ``"error"``.
        measurements: One row per ``measure`` step that ran — each the
            step's ``result`` output (``name``, ``value``, ``unit``,
            ``limits``, ``pass``) plus ``step`` (the step name). Empty when
            no ``measure`` step ran, including a guard failure or an error
            that stopped the run before any completed.
        detail: The one-line reason for ``fail``/``error``; ``None`` for
            ``pass``.
    """

    status: VerdictStatus
    measurements: list[dict[str, Any]] = field(default_factory=list)
    detail: str | None = None


def _measurement_rows(result: ExecutionResult) -> list[dict[str, Any]]:
    """One row per ``measure`` step in *result*: its ``result`` output plus ``step``."""
    rows: list[dict[str, Any]] = []
    for step in result.steps:
        if step.brick_name != "measure":
            continue
        row = step.outputs.get("result")
        if isinstance(row, dict):
            rows.append({"step": step.step_name, **row})
    return rows


def _format_limits(limits: dict[str, Any]) -> str:
    """``[min, max]``, with a missing bound written as an open end."""
    lo = limits.get("min")
    hi = limits.get("max")
    return f"[{'-inf' if lo is None else lo}, {'inf' if hi is None else hi}]"


def _format_failure(row: dict[str, Any]) -> str:
    """One-line reason a measurement row failed, e.g. ``vout 4.7 V not in [4.9, 5.1]``."""
    name, value, unit = row.get("name"), row.get("value"), row.get("unit")
    limits = row.get("limits") or {}
    if not limits:
        return f"{name} {value} {unit} is not a finite value"
    return f"{name} {value} {unit} not in {_format_limits(limits)}"


def derive_verdict(result: ExecutionResult) -> Verdict:
    """Derive the verdict for a run that completed (did not raise).

    ``fail`` if any ``measure`` step's row has ``pass: false`` (the first
    such row is used for ``detail``); ``pass`` otherwise. Pure: reads only
    ``result.steps`` where ``brick_name == "measure"``.
    """
    rows = _measurement_rows(result)
    failing = [row for row in rows if row.get("pass") is False]
    if failing:
        return Verdict(status="fail", measurements=rows, detail=_format_failure(failing[0]))
    return Verdict(status="pass", measurements=rows)


def verdict_for_guard_failure(exc: GuardFailedError) -> Verdict:
    """The verdict for a run a guard stopped: ``fail`` — the run did what it should."""
    return Verdict(status="fail", detail=str(exc).splitlines()[0])


def verdict_for_error(exc: BrickError) -> Verdict:
    """The verdict for a run any other ``BrickError`` ended: ``error``."""
    return Verdict(status="error", detail=str(exc).splitlines()[0])
