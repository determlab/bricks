"""Tests for issue #66 bug A — ``@flow`` must wire parameters to ``${inputs.X}``.

Before the fix, ``@flow`` traced the decorated function with ``None``
substituted for every parameter, so a pipeline as simple as
``step.reduce_sum(values=values)`` recorded ``params={"values": None}``
on the step. The engine then called ``reduce_sum(values=None)`` and
crashed with ``'NoneType' object is not iterable``.

The fix introduces :class:`~bricks.core.dsl.InputRef` sentinels, threaded
through the trace so the DAG serialiser emits
``params={"values": "${inputs.values}"}`` and populates
``blueprint.inputs`` so the orchestrator's ``InputMapper`` can bind the
runtime value. This suite guards all three links in that chain plus the
end-to-end engine run that the issue reporter reproduced.
"""

from __future__ import annotations

from bricks.core.builtins import register_builtins
from bricks.core.dsl import flow, for_each, step
from bricks.core.engine import BlueprintEngine
from bricks.core.registry import BrickRegistry


def _registry_with(name: str, fn: object) -> BrickRegistry:
    """Build a registry with the given brick plus builtins registered."""
    from bricks.core.models import BrickMeta

    reg = BrickRegistry()
    reg.register(name, fn, BrickMeta(name=name, description="test", category="test"))
    register_builtins(reg)
    return reg


def test_flow_param_rewrites_step_params_to_inputs_reference() -> None:
    """``@flow def f(values): step.X(values=values)`` must emit
    ``params={"values": "${inputs.values}"}`` — not a literal None."""

    @flow
    def my_pipeline(values):  # type: ignore[no-untyped-def]
        """Sum a list."""
        return step.reduce_sum(values=values)

    bp = my_pipeline.to_blueprint()
    assert len(bp.steps) == 1
    assert bp.steps[0].params == {"values": "${inputs.values}"}


def test_flow_populates_blueprint_inputs_schema() -> None:
    """``blueprint.inputs`` must list every flow parameter so the
    orchestrator's InputMapper knows which runtime values to bind."""

    @flow
    def my_pipeline(values):  # type: ignore[no-untyped-def]
        return step.reduce_sum(values=values)

    bp = my_pipeline.to_blueprint()
    assert bp.inputs == {"values": "Any"}


def test_flow_executes_end_to_end_through_engine() -> None:
    """Blueprint-layer round-trip: engine.run(bp, inputs={"values": [...]})
    resolves ``${inputs.values}`` and reaches the brick with the real list.
    This is the exact scenario the issue reporter's $2.04 repro hit."""

    captured: dict[str, object] = {}

    def reduce_sum(values: list[float]) -> dict[str, float]:
        captured["values"] = values
        return {"result": float(sum(values))}

    @flow
    def sum_pipeline(values):  # type: ignore[no-untyped-def]
        return step.reduce_sum(values=values)

    bp = sum_pipeline.to_blueprint()
    reg = _registry_with("reduce_sum", reduce_sum)
    engine = BlueprintEngine(registry=reg)
    result = engine.run(bp, inputs={"values": [1.0, 2.0, 3.0]})

    assert captured["values"] == [1.0, 2.0, 3.0], "brick received literal None pre-fix"
    assert result.outputs == {"result": 6.0}


def test_flow_for_each_items_binds_to_input_list() -> None:
    """Regression for the other shape from issue #66:
    ``@flow def f(records): for_each(items=records, ...)`` must bind
    the iteration list to the runtime input, not to an empty ``[]``."""

    def echo(item: int) -> dict[str, int]:
        return {"result": item * 2}

    @flow
    def double_each(records):  # type: ignore[no-untyped-def]
        return for_each(items=records, do=lambda r: step.echo(item=r))

    bp = double_each.to_blueprint()
    assert bp.inputs == {"records": "Any"}
    # The for_each step's items slot must reference the runtime input —
    # not the empty-list fallback that used to be the silent failure mode.
    for_each_step = next(s for s in bp.steps if s.brick == "__for_each__")
    assert for_each_step.params["items"] == "${inputs.records}"

    reg = _registry_with("echo", echo)
    engine = BlueprintEngine(registry=reg)
    result = engine.run(bp, inputs={"records": [1, 2, 3]})
    assert result.outputs["result"] == [{"result": 2}, {"result": 4}, {"result": 6}]
