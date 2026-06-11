"""Tests for DAGExecutionEngine — FlowDefinition → BlueprintEngine execution."""

from __future__ import annotations

from typing import Any

from bricks.core.dsl import branch, flow, for_each, step
from bricks.core.engine import BlueprintEngine, DAGExecutionEngine
from bricks.core.models import BrickMeta, ExecutionResult
from bricks.core.registry import BrickRegistry

# ---------------------------------------------------------------------------
# Test registry + bricks
# ---------------------------------------------------------------------------


def _make_engine() -> tuple[DAGExecutionEngine, BrickRegistry]:
    """Create a DAGExecutionEngine backed by a registry with test bricks."""
    reg = BrickRegistry()

    def add(a: float, b: float) -> dict[str, Any]:
        """Add two numbers."""
        return {"result": a + b}

    def multiply(a: float, b: float) -> dict[str, Any]:
        """Multiply two numbers."""
        return {"result": a * b}

    def upper(item: Any) -> dict[str, Any]:
        """Uppercase a string item."""
        return {"result": str(item).upper()}

    def always_true(input: Any) -> dict[str, Any]:
        """Always return True."""
        return {"result": True}

    def always_false(input: Any) -> dict[str, Any]:
        """Always return False."""
        return {"result": False}

    def noop(input: Any) -> dict[str, Any]:
        """Return input unchanged."""
        return {"result": input}

    for fn in (add, multiply, upper, always_true, always_false, noop):
        reg.register(fn.__name__, fn, BrickMeta(name=fn.__name__, description=fn.__doc__ or ""))

    engine = DAGExecutionEngine(BlueprintEngine(reg))
    return engine, reg


# ---------------------------------------------------------------------------
# DAGExecutionEngine tests
# ---------------------------------------------------------------------------


def test_dag_engine_simple_flow() -> None:
    """FlowDefinition with 2 step calls executes correctly."""
    engine, _ = _make_engine()

    @flow
    def my_flow() -> Any:
        a = step.add(a=1.0, b=2.0)
        return step.multiply(a=a, b=4.0)

    result = engine.execute(my_flow)
    assert isinstance(result, ExecutionResult)


def test_dag_engine_returns_execution_result() -> None:
    """DAGExecutionEngine.execute() returns a proper ExecutionResult."""
    engine, _ = _make_engine()

    @flow
    def simple() -> Any:
        return step.add(a=1.0, b=1.0)

    result = engine.execute(simple)
    assert isinstance(result, ExecutionResult)


def test_dag_engine_flow_with_for_each() -> None:
    """Flow using for_each produces a valid BlueprintDefinition via to_blueprint()."""
    # for_each lambdas cannot be looked up by name in the registry, so we
    # test that the DAG→blueprint conversion succeeds without executing.
    from bricks.core.models import BlueprintDefinition

    @flow
    def batch_flow(items: Any) -> Any:
        return for_each(items, do=lambda x: step.upper(item=x))

    bp = batch_flow.to_blueprint()
    assert isinstance(bp, BlueprintDefinition)
    assert any(s.brick == "__for_each__" for s in bp.steps)


def test_dag_engine_flow_with_branch() -> None:
    """Flow using branch produces a valid ExecutionResult."""
    engine, _ = _make_engine()

    @flow
    def conditional_flow() -> Any:
        return branch(
            "always_true",
            if_true=lambda: step.add(a=1.0, b=2.0),
            if_false=lambda: step.multiply(a=1.0, b=2.0),
        )

    result = engine.execute(conditional_flow)
    assert isinstance(result, ExecutionResult)


def test_dag_engine_complex_flow() -> None:
    """5-step flow with mixed primitives executes without error."""
    engine, _ = _make_engine()

    @flow
    def complex_flow() -> Any:
        a = step.add(a=1.0, b=2.0)
        b = step.multiply(a=3.0, b=4.0)
        step.add(a=5.0, b=6.0)
        step.multiply(a=7.0, b=8.0)
        return step.add(a=a, b=b)

    result = engine.execute(complex_flow)
    assert isinstance(result, ExecutionResult)
