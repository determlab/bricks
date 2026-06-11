"""Public Python API for the Bricks engine — deterministic, no LLM.

Usage::

    from bricks import build_default_registry, run_blueprint

    # Execute a blueprint YAML file against inputs — pure Python, zero tokens
    result = run_blueprint("blueprints/revenue.yaml", inputs={"values": [1, 2, 3]})
    print(result.outputs)

Natural-language task execution (LLM composition) lives in the separate
``bricks_ai`` package — see :class:`bricks_ai.Bricks`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bricks.core.engine import BlueprintEngine
from bricks.core.loader import BlueprintLoader
from bricks.core.models import ExecutionResult, Verbosity
from bricks.core.registry import BrickRegistry
from bricks.core.validation import BlueprintValidator


def build_default_registry() -> BrickRegistry:
    """Build the default registry by discovering installed brick packs.

    Also registers DSL control-flow builtins (``__for_each__`` / ``__branch__``).
    Without this, any blueprint that wraps iteration in ``for_each``
    fails at execute() with ``BrickNotFoundError: '__for_each__'`` —
    issue #66 bug B.

    Returns:
        A :class:`~bricks.core.registry.BrickRegistry` populated with all
        bricks from every installed pack plus DSL builtins.

    Raises:
        BricksConfigError: If no packs (e.g. ``bricks-stdlib``) are installed.
    """
    from bricks.core.builtins import register_builtins  # noqa: PLC0415
    from bricks.packs import discover_and_load  # noqa: PLC0415

    reg = BrickRegistry()
    discover_and_load(reg)
    register_builtins(reg)
    return reg


def run_blueprint(
    source: str | Path,
    inputs: dict[str, Any] | None = None,
    *,
    registry: BrickRegistry | None = None,
    verbosity: Verbosity = Verbosity.MINIMAL,
) -> ExecutionResult:
    """Load, validate, and execute a blueprint — deterministic, no LLM.

    Args:
        source: Path to a blueprint YAML file, or a YAML document string
            (anything containing a newline is treated as YAML content).
        inputs: Input values for ``${inputs.X}`` references in the blueprint.
        registry: Optional custom brick registry. Defaults to all bricks from
            installed packs plus DSL builtins.
        verbosity: Output detail level for the execution result.

    Returns:
        The :class:`~bricks.core.models.ExecutionResult` with outputs,
        per-step traces, and timing.

    Raises:
        YamlLoadError: If the YAML cannot be parsed.
        BlueprintValidationError: If the blueprint references unknown bricks
            or is otherwise invalid.
        BrickExecutionError: If a step fails during execution.
    """
    reg = registry if registry is not None else build_default_registry()
    loader = BlueprintLoader()
    if isinstance(source, Path):
        blueprint = loader.load_file(source)
    elif "\n" in source:
        blueprint = loader.load_string(source)
    else:
        blueprint = loader.load_file(Path(source))
    BlueprintValidator(registry=reg).validate(blueprint)
    engine = BlueprintEngine(registry=reg)
    return engine.run(blueprint, inputs=inputs or None, verbosity=verbosity)
