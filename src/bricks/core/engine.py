"""BlueprintEngine: loads and executes YAML blueprints."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from bricks.core.brick import BaseBrick, BrickModel
from bricks.core.context import ExecutionContext
from bricks.core.exceptions import BrickExecutionError, GuardFailedError
from bricks.core.models import (
    BlueprintDefinition,
    BrickMeta,
    ExecutionResult,
    StepDefinition,
    StepResult,
    Verbosity,
)
from bricks.core.registry import BrickRegistry
from bricks.core.resolver import ReferenceResolver


def _call_teardown(
    callable_: Any,
    resolved_params: dict[str, Any],
    meta: BrickMeta,
    error: Exception,
) -> None:
    """Call teardown on a brick (class-based or function-based), suppressing exceptions.

    Args:
        callable_: The brick callable.
        resolved_params: The resolved parameter dict passed to the brick.
        meta: Brick metadata.
        error: The original execution error.
    """
    try:
        if isinstance(callable_, BaseBrick):
            callable_.teardown(BrickModel(), meta, error)
        elif hasattr(callable_, "__brick_teardown__") and callable_.__brick_teardown__ is not None:
            callable_.__brick_teardown__(resolved_params, error)
    except Exception:  # noqa: S110
        pass  # Never mask the original error


class BlueprintEngine:
    """Executes a validated BlueprintDefinition step-by-step.

    Each step resolves its parameter references, looks up the brick
    in the registry, executes it, and optionally saves the result.

    Steps may reference a ``brick`` (registered callable) or a ``blueprint``
    (path to a child YAML file), enabling sub-blueprint composition.

    On failure, teardown is called on the failing step, then in reverse
    order on all previously completed steps, before re-raising.

    The ``verbosity`` parameter controls how much execution detail is included
    in the returned :class:`~bricks.core.models.ExecutionResult`:

    - ``MINIMAL`` (default): final ``outputs`` only.
    - ``STANDARD``: ``outputs`` + per-step output dicts.
    - ``FULL``: ``outputs`` + per-step inputs/outputs/timing + total duration.
    """

    _MAX_DEPTH: int = 10

    def __init__(
        self,
        registry: BrickRegistry,
        loader: Any | None = None,
        plugin_manager: Any | None = None,
    ) -> None:
        """Initialise the engine.

        Args:
            registry: The brick registry to use for step execution.
            loader: Optional BlueprintLoader. Defaults to a new BlueprintLoader instance.
            plugin_manager: Optional ``pluggy.PluginManager`` for lifecycle
                hooks (see :mod:`bricks.core.hooks`). When ``None`` no
                hooks fire — production paths incur zero cost.
        """
        from bricks.core.loader import BlueprintLoader  # noqa: PLC0415 — avoid circular at module level

        self._registry = registry
        self._loader: BlueprintLoader = loader if loader is not None else BlueprintLoader()
        self._resolver = ReferenceResolver()
        self._pm = plugin_manager

    def run(
        self,
        blueprint: BlueprintDefinition,
        inputs: dict[str, Any] | None = None,
        verbosity: Verbosity = Verbosity.MINIMAL,
    ) -> ExecutionResult:
        """Execute a blueprint and return a structured result.

        Args:
            blueprint: A validated BlueprintDefinition.
            inputs: Runtime input values matching the blueprint's input schema.
            verbosity: Controls execution trace detail in the returned result.

        Returns:
            An :class:`~bricks.core.models.ExecutionResult` with ``outputs``
            always populated. ``steps`` and timing fields populated according
            to ``verbosity``.

        Raises:
            BrickExecutionError: If any step fails during execution.
        """
        return self._execute(blueprint, inputs, depth=0, verbosity=verbosity)

    def _execute(
        self,
        blueprint: BlueprintDefinition,
        inputs: dict[str, Any] | None,
        depth: int,
        verbosity: Verbosity = Verbosity.MINIMAL,
    ) -> ExecutionResult:
        """Internal recursive execution helper.

        Args:
            blueprint: The blueprint to execute.
            inputs: Runtime inputs.
            depth: Current recursion depth (0 = top level).
            verbosity: Execution trace detail level.

        Returns:
            An ExecutionResult.

        Raises:
            BrickExecutionError: On step failure or recursion depth exceeded.
        """
        if depth > self._MAX_DEPTH:
            raise BrickExecutionError(
                brick_name="<sub-blueprint>",
                step_name="<depth-check>",
                cause=RecursionError(f"Sub-blueprint recursion depth exceeded (max {self._MAX_DEPTH})"),
            )

        context = ExecutionContext(inputs=inputs)
        completed: list[tuple[Any, dict[str, Any], BrickMeta]] = []
        step_results: list[StepResult] = []
        total_start = time.perf_counter()

        for step in blueprint.steps:
            resolved_params = self._resolver.resolve(step.params, context)
            result, step_result = self._execute_step(
                step,
                resolved_params,
                completed,
                depth,
                verbosity,
                context,
            )

            if step_result is not None:
                step_results.append(step_result)

            if step.save_as is not None:
                context.save_result(step.save_as, result)
            context.advance_step()

        outputs: dict[str, Any] = self._resolver.resolve(blueprint.outputs_map, context)
        total_ms = (time.perf_counter() - total_start) * 1000

        return ExecutionResult(
            outputs=outputs,
            steps=step_results,
            total_duration_ms=total_ms if verbosity == Verbosity.FULL else 0.0,
            blueprint_name=blueprint.name,
            verbosity=verbosity,
        )

    def _execute_step(
        self,
        step: StepDefinition,
        resolved_params: dict[str, Any],
        completed: list[tuple[Any, dict[str, Any], BrickMeta]],
        depth: int,
        verbosity: Verbosity,
        context: ExecutionContext,
    ) -> tuple[Any, StepResult | None]:
        """Execute a single step (brick, sub-blueprint, or guard).

        Args:
            step: The step definition to execute.
            resolved_params: Pre-resolved parameters for this step.
            completed: Mutable list of completed steps for teardown tracking.
            depth: Current recursion depth.
            verbosity: Execution trace detail level.
            context: Current execution context (used by guard steps).

        Returns:
            Tuple of (step result value, optional StepResult for tracing).

        Raises:
            BrickExecutionError: If the step fails.
            GuardFailedError: If a guard condition evaluates to False.
        """
        if step.type == "guard":
            return self._execute_guard_step(step, context)
        if step.brick is not None:
            return self._execute_brick_step(step, resolved_params, completed, verbosity)
        return self._execute_sub_blueprint_step(step, resolved_params, depth, verbosity)

    def _execute_brick_step(
        self,
        step: StepDefinition,
        resolved_params: dict[str, Any],
        completed: list[tuple[Any, dict[str, Any], BrickMeta]],
        verbosity: Verbosity,
    ) -> tuple[Any, StepResult | None]:
        """Execute a function/class-based brick step.

        Args:
            step: The step definition.
            resolved_params: Pre-resolved parameters.
            completed: Mutable list for teardown tracking.
            verbosity: Trace detail level.

        Returns:
            Tuple of (result value, optional StepResult).
        """
        brick_name: str = step.brick  # type: ignore[assignment]  # guaranteed non-None by caller
        callable_, meta = self._registry.get(brick_name)

        # Fire step_start for top-level user bricks only. Internal wrapper
        # primitives would flood the UI with per-iteration events; the outer
        # wrapper step still emits its own start/done.
        if self._pm is not None:
            self._pm.hook.step_start(step_name=step.name, brick_name=brick_name)

        t0 = time.perf_counter()
        try:
            result = callable_(**resolved_params)
        except BrickExecutionError as exc:
            # Already attributed by an inner primitive (for_each / branch /
            # sub-blueprint). Run teardown, then propagate unchanged so the
            # real failing brick's name survives. See issue #34.
            _call_teardown(callable_, resolved_params, meta, exc)
            for prev_callable, prev_params, prev_meta in reversed(completed):
                _call_teardown(prev_callable, prev_params, prev_meta, exc)
            raise
        except Exception as exc:
            _call_teardown(callable_, resolved_params, meta, exc)
            for prev_callable, prev_params, prev_meta in reversed(completed):
                _call_teardown(prev_callable, prev_params, prev_meta, exc)
            raise BrickExecutionError(
                brick_name=brick_name,
                step_name=step.name,
                cause=exc,
            ) from exc

        duration_ms = (time.perf_counter() - t0) * 1000
        completed.append((callable_, resolved_params, meta))

        if self._pm is not None:
            self._pm.hook.step_done(
                step_name=step.name,
                brick_name=brick_name,
                duration_ms=int(duration_ms),
            )

        step_result: StepResult | None = None
        if verbosity in (Verbosity.STANDARD, Verbosity.FULL):
            step_result = StepResult(
                step_name=step.name,
                brick_name=brick_name,
                inputs=resolved_params if verbosity == Verbosity.FULL else {},
                outputs=result if isinstance(result, dict) else {},
                duration_ms=duration_ms if verbosity == Verbosity.FULL else 0.0,
                save_as=step.save_as,
            )

        return result, step_result

    def _execute_sub_blueprint_step(
        self,
        step: StepDefinition,
        resolved_params: dict[str, Any],
        depth: int,
        verbosity: Verbosity,
    ) -> tuple[Any, StepResult | None]:
        """Execute a sub-blueprint step.

        Args:
            step: The step definition.
            resolved_params: Pre-resolved parameters.
            depth: Current recursion depth.
            verbosity: Trace detail level.

        Returns:
            Tuple of (result value, optional StepResult).
        """
        child_path = Path(step.blueprint or "")
        try:
            child_bp = self._loader.load_file(child_path)
            child_result = self._execute(child_bp, resolved_params, depth + 1, verbosity)
            result = child_result.outputs
        except BrickExecutionError:
            raise
        except Exception as exc:
            raise BrickExecutionError(
                brick_name=step.blueprint or "<sub-blueprint>",
                step_name=step.name,
                cause=exc,
            ) from exc

        step_result: StepResult | None = None
        if verbosity in (Verbosity.STANDARD, Verbosity.FULL):
            step_result = StepResult(
                step_name=step.name,
                brick_name=step.blueprint or "<sub-blueprint>",
                inputs=resolved_params if verbosity == Verbosity.FULL else {},
                outputs=result if isinstance(result, dict) else {},
                save_as=step.save_as,
            )

        return result, step_result

    def _execute_guard_step(
        self,
        step: StepDefinition,
        context: ExecutionContext,
    ) -> tuple[None, None]:
        """Evaluate a guard condition against the current execution context.

        The condition is evaluated with a restricted scope: all named step
        results saved so far, plus ``__builtins__`` set to an empty dict.

        Args:
            step: The guard step definition (must have ``condition`` set).
            context: Current execution context providing variable bindings.

        Returns:
            ``(None, None)`` when the condition passes.

        Raises:
            GuardFailedError: When the condition evaluates to a falsy value.
        """
        condition: str = step.condition  # type: ignore[assignment]  # validated non-None
        scope: dict[str, Any] = dict(context.results)
        try:
            passed = bool(eval(condition, {"__builtins__": {}}, scope))  # noqa: S307
        except Exception as exc:
            raise GuardFailedError(
                step_name=step.name,
                condition=condition,
                message=f"Condition raised an error: {exc}",
                actual=str(scope)[:200],
            ) from exc

        if not passed:
            raise GuardFailedError(
                step_name=step.name,
                condition=condition,
                message=step.message,
                actual=str(scope)[:200],
            )
        return None, None


class DAGExecutionEngine:
    """Executes a :class:`~bricks.core.dsl.FlowDefinition` through :class:`BlueprintEngine`.

    Converts ``FlowDefinition → BlueprintDefinition → BlueprintEngine.run()``.
    Built-in DSL bricks (``__for_each__``, ``__branch__``) are registered
    automatically when this engine is created.

    Args:
        engine: The underlying :class:`BlueprintEngine` to delegate to.
    """

    def __init__(self, engine: BlueprintEngine) -> None:
        """Initialise the DAGExecutionEngine.

        Args:
            engine: A :class:`BlueprintEngine` instance. Built-in bricks are
                registered into its registry on construction.
        """
        from bricks.core.builtins import register_builtins  # noqa: PLC0415

        self._engine = engine
        register_builtins(engine._registry)

    def execute(
        self,
        flow_def: Any,
        inputs: dict[str, Any] | None = None,
        verbosity: Verbosity = Verbosity.MINIMAL,
    ) -> ExecutionResult:
        """Execute a :class:`~bricks.core.dsl.FlowDefinition`.

        Args:
            flow_def: The ``FlowDefinition`` to execute.
            inputs: Runtime input values for ``${inputs.X}`` references.
            verbosity: Controls execution trace detail in the returned result.

        Returns:
            :class:`~bricks.core.models.ExecutionResult` from the engine.
        """
        blueprint = flow_def.to_blueprint()
        return self._engine.run(blueprint, inputs or {}, verbosity=verbosity)
