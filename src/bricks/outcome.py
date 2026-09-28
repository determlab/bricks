"""Run a blueprint for one unit and return its verdict (#59).

:func:`run_for_unit` is the one path from a blueprint to a
:class:`~bricks.verdict.Verdict`: ``bricks run`` in the CLI and Python callers
both go through it. It never raises for a failing unit — a guard that stops the
run is ``fail`` and any other :class:`~bricks.core.exceptions.BrickError`
(bad YAML, an invalid blueprint, a missing brick, a failing step) is ``error``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from bricks.api import build_default_registry
from bricks.core.engine import BlueprintEngine
from bricks.core.exceptions import BrickError, GuardFailedError
from bricks.core.loader import BlueprintLoader
from bricks.core.models import BlueprintDefinition, ExecutionResult, Verbosity
from bricks.core.registry import BrickRegistry
from bricks.core.validation import BlueprintValidator
from bricks.verdict import Verdict, derive_verdict, verdict_for_error, verdict_for_guard_failure


class RunOutcome(BaseModel):
    """What running a blueprint for one unit produced.

    Attributes:
        verdict: The derived pass/fail/error verdict.
        result: The engine result; ``None`` when the run raised (guard or error).
        unit: The unit id the run was for.
        error: The ``BrickError`` that ended the run, or ``None`` when it completed.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    verdict: Verdict
    result: ExecutionResult | None = None
    unit: str
    error: BrickError | None = None


def execute_for_unit(
    blueprint: BlueprintDefinition,
    registry: BrickRegistry,
    inputs: dict[str, Any] | None,
    unit: str,
    verbosity: Verbosity = Verbosity.STANDARD,
    *,
    validate: bool = True,
) -> RunOutcome:
    """Run an already-loaded *blueprint* and turn the result or exception into an outcome.

    The single verdict path: :func:`run_for_unit` and ``bricks run`` both call it.
    The CLI passes ``validate=False`` because ``bricks run`` does not validate
    (G8 in docs/DECISIONS.md).
    """
    try:
        if validate:
            BlueprintValidator(registry=registry).validate(blueprint)
        result = BlueprintEngine(registry=registry).run(blueprint, inputs=inputs or None, verbosity=verbosity)
    except GuardFailedError as exc:
        return RunOutcome(verdict=verdict_for_guard_failure(exc), unit=unit, error=exc)
    except BrickError as exc:
        return RunOutcome(verdict=verdict_for_error(exc), unit=unit, error=exc)
    return RunOutcome(verdict=derive_verdict(result), result=result, unit=unit)


def run_for_unit(
    source: str | Path,
    inputs: dict[str, Any] | None = None,
    *,
    unit: str = "bench",
    registry: BrickRegistry | None = None,
) -> RunOutcome:
    """Load, validate and run a blueprint for *unit*; return its verdict.

    Runs at ``Verbosity.STANDARD`` (the verdict reads each step's output).
    Never raises on a failing unit: see the module docstring.

    Args:
        source: Path to a blueprint YAML file, or a YAML string (anything
            containing a newline is treated as YAML content).
        inputs: Input values for ``${inputs.X}`` references.
        unit: The unit id, carried into the outcome.
        registry: Optional custom registry; defaults to all installed packs.

    Returns:
        A :class:`RunOutcome`.
    """
    reg = registry if registry is not None else build_default_registry()
    loader = BlueprintLoader()
    try:
        if isinstance(source, Path):
            blueprint = loader.load_file(source)
        elif "\n" in source:
            blueprint = loader.load_string(source)
        else:
            blueprint = loader.load_file(Path(source))
    except BrickError as exc:
        return RunOutcome(verdict=verdict_for_error(exc), unit=unit, error=exc)
    return execute_for_unit(blueprint, reg, inputs, unit)
