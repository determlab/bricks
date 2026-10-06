"""Run a blueprint for one unit and get its verdict (#59).

:func:`run_for_unit` is the one call behind ``bricks run``: it runs a blueprint
for a unit and returns a :class:`RunOutcome`. It never raises on a failing unit
or a failing run — a guard stop is ``fail``, any other ``BrickError`` (or an
unreadable blueprint file) is ``error``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, PrivateAttr

from bricks.api import build_default_registry
from bricks.core.engine import BlueprintEngine
from bricks.core.exceptions import BrickError, GuardFailedError, MissingInputError
from bricks.core.loader import BlueprintLoader
from bricks.core.models import BlueprintDefinition, ExecutionResult, Verbosity
from bricks.core.registry import BrickRegistry
from bricks.core.validation import BlueprintValidator
from bricks.verdict import Verdict, derive_verdict, verdict_for_error, verdict_for_guard_failure


class RunOutcome(BaseModel):
    """What running a blueprint for one unit produced.

    Attributes:
        verdict: ``pass``, ``fail`` or ``error``, with measurements and reason.
        result: The engine result; ``None`` when the run raised (a guard stop,
            a brick error, an unreadable blueprint).
        unit: The unit the run was for.
    """

    verdict: Verdict
    result: ExecutionResult | None = None
    unit: str

    _error: BrickError | None = PrivateAttr(default=None)

    @property
    def error(self) -> BrickError | None:
        """The ``BrickError`` that ended the run (a guard stop included), else ``None``."""
        return self._error


def _find_guard_failure(exc: BaseException) -> GuardFailedError | None:
    """The ``GuardFailedError`` in *exc*'s chain (itself, cause, context), if any."""
    seen: set[int] = set()
    stack: list[BaseException | None] = [exc]
    while stack:
        cur = stack.pop()
        if cur is None or id(cur) in seen:
            continue
        seen.add(id(cur))
        if isinstance(cur, GuardFailedError):
            return cur
        stack.extend([cur.__cause__, cur.__context__, getattr(cur, "cause", None)])
    return None


def _outcome_from_error(unit: str, exc: BrickError) -> RunOutcome:
    guard = _find_guard_failure(exc)
    verdict = verdict_for_guard_failure(guard) if guard is not None else verdict_for_error(exc)
    outcome = RunOutcome(verdict=verdict, unit=unit)
    outcome._error = guard if guard is not None else exc
    return outcome


def run_for_unit(
    source: str | Path | BlueprintDefinition,
    inputs: dict[str, Any] | None = None,
    *,
    unit: str = "bench",
    registry: BrickRegistry | None = None,
    verbosity: Verbosity = Verbosity.STANDARD,
) -> RunOutcome:
    """Run a blueprint for *unit* and return its verdict. Never raises on a failing run.

    Validates the blueprint before the first step (G8, #87): an invalid
    blueprint — an unknown brick reference, say — ends the run as ``error``
    with zero steps executed, the same ``BlueprintValidator`` pass
    :func:`bricks.api.run_blueprint` already runs, never reaching a brick
    that might drive hardware.

    Args:
        source: A blueprint file path, a YAML string (anything with a newline),
            or an already loaded blueprint.
        inputs: Input values for ``${inputs.X}`` references.
        unit: The unit under test, carried on the outcome.
        registry: Brick registry; defaults to every installed pack.
        verbosity: ``STANDARD`` (default) or ``FULL`` (adds timings); ``MINIMAL``
            is raised to ``STANDARD`` because the verdict reads step output.

    Returns:
        A :class:`RunOutcome`.
    """
    if unit is not None and not unit.strip():
        verdict = Verdict(status="error", detail="unit must not be blank (leave it out for 'bench')")
        return RunOutcome(verdict=verdict, unit=unit)
    run_verbosity = Verbosity.STANDARD if verbosity == Verbosity.MINIMAL else verbosity
    try:
        if isinstance(source, BlueprintDefinition):
            blueprint = source
        else:
            loader = BlueprintLoader()
            if isinstance(source, str) and "\n" in source:
                blueprint = loader.load_string(source)
            else:
                path = Path(source)
                try:
                    blueprint = loader.load_file(path)
                except (OSError, UnicodeDecodeError) as exc:
                    verdict = Verdict(status="error", detail=f"Cannot read blueprint {path}: {exc}")
                    return RunOutcome(verdict=verdict, unit=unit)
        missing = [name for name in blueprint.inputs if name not in (inputs or {})]
        if missing:
            raise MissingInputError(missing)
        reg = registry if registry is not None else build_default_registry()
        BlueprintValidator(registry=reg).validate(blueprint)
        result = BlueprintEngine(registry=reg).run(blueprint, inputs=inputs or None, verbosity=run_verbosity)
    except BrickError as exc:
        return _outcome_from_error(unit, exc)
    return RunOutcome(verdict=derive_verdict(result), result=result, unit=unit)


__all__ = ["RunOutcome", "run_for_unit"]
