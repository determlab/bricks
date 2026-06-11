"""Tests for ``for_each`` static-kwarg propagation (issue #63).

Before the fix, ``for_each(items=..., do=lambda x: step.Y(a=x, b=CONST))``
dropped ``b=CONST`` on the floor — the inner brick was invoked with only
the per-item kwarg, so any brick that required more than one arg crashed
with ``TypeError: missing 1 required positional argument``. This suite
guards the post-fix contract.
"""

from __future__ import annotations

from typing import Any

import pytest

from bricks.core.builtins import register_builtins
from bricks.core.dsl import FlowDefinition, flow, for_each, step
from bricks.core.engine import BlueprintEngine
from bricks.core.models import BrickMeta
from bricks.core.registry import BrickRegistry


def _make_registry() -> BrickRegistry:
    reg = BrickRegistry()
    register_builtins(reg)

    def add(a: int, b: int) -> dict[str, int]:
        return {"result": a + b}

    reg.register("add", add, BrickMeta(name="add", description="add a + b"))

    def rename_dict_keys(input: dict[str, Any], rename_map: dict[str, str]) -> dict[str, Any]:
        return {"result": {rename_map.get(k, k): v for k, v in input.items()}}

    reg.register(
        "rename_dict_keys",
        rename_dict_keys,
        BrickMeta(name="rename_dict_keys", description="rename keys"),
    )

    def double(x: int) -> dict[str, int]:
        return {"result": x * 2}

    reg.register("double", double, BrickMeta(name="double", description="x2"))

    return reg


def _flow_to_outputs(fn: Any, **inputs: Any) -> dict[str, Any]:
    """Compile a ``@flow`` decorator'd function and run it through the real engine.

    Uses ``FlowDefinition.execute`` so the tracer sees the actual runtime
    values — crucial for the multi-arg case where the trace happens at
    execute time, not at decorator time.
    """
    flow_def: FlowDefinition = fn  # type: ignore[assignment]
    engine = BlueprintEngine(registry=_make_registry())
    return flow_def.execute(inputs=inputs, engine=engine)


def test_for_each_preserves_static_kwarg() -> None:
    """``b=10`` must survive the for_each round-trip — this is the repro
    case from issue #63, reduced to its minimum shape."""

    @flow
    def add_ten(xs: list[int]) -> Any:
        return for_each(items=xs, do=lambda x: step.add(a=x, b=10))

    out = _flow_to_outputs(add_ten, xs=[1, 2, 3])
    # The single-output flow puts the result under ``outputs["result"]``; the
    # for_each builtin returns a dict with both ``result`` and ``results``
    # aliases pointing at the per-item list.
    per_item = out["result"] if isinstance(out.get("result"), list) else out["result"]["result"]
    values = [r["result"] if isinstance(r, dict) else r for r in per_item]
    assert values == [11, 12, 13], values


def test_for_each_preserves_complex_static_kwarg() -> None:
    """The Orders-scenario pattern: a dict literal closed over by the lambda
    reaches the inner brick intact."""

    @flow
    def rename_rows(rows: list[dict[str, Any]]) -> Any:
        return for_each(
            items=rows,
            do=lambda row: step.rename_dict_keys(input=row, rename_map={"id": "customer_id"}),
        )

    rows = [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]
    out = _flow_to_outputs(rename_rows, rows=rows)
    per_item = out["result"] if isinstance(out.get("result"), list) else out["result"]["result"]
    shapes = [r["result"] if isinstance(r, dict) else r for r in per_item]
    assert shapes == [
        {"customer_id": 1, "name": "a"},
        {"customer_id": 2, "name": "b"},
    ]


def test_for_each_rejects_lambda_closing_over_another_node() -> None:
    """A lambda that references another step's output (a Node) must fail
    *at compose time* with a clear message — supporting that would require
    per-iteration DAG build, explicitly out of scope."""

    with pytest.raises(ValueError, match="for_each: do= lambda may not reference another step's output"):

        @flow
        def bad(xs: list[int]) -> Any:
            other = step.double(x=5)
            return for_each(
                items=xs,
                do=lambda x: step.add(a=x, b=other.output),
            )

        # Evaluating the flow attribute triggers the trace — the error fires
        # inside for_each() at trace time.
        _ = bad


def test_for_each_single_kwarg_still_works() -> None:
    """Regression guard: the no-static-kwarg case (already working after
    #58) must keep working — static_kwargs defaults to an empty dict."""

    @flow
    def doubles(xs: list[int]) -> Any:
        return for_each(items=xs, do=lambda x: step.double(x=x))

    out = _flow_to_outputs(doubles, xs=[1, 2, 3])
    per_item = out["result"] if isinstance(out.get("result"), list) else out["result"]["result"]
    values = [r["result"] if isinstance(r, dict) else r for r in per_item]
    assert values == [2, 4, 6]


def test_for_each_item_kwarg_wins_on_conflict() -> None:
    """If the lambda passes a static kwarg named the same as the item
    binding, the per-item kwarg must win — otherwise iteration is a no-op
    on every item. Hypothetical but easy to guard."""

    @flow
    def run(xs: list[int]) -> Any:
        # ``a`` is both the item kwarg and a closure key; per-item wins.
        return for_each(items=xs, do=lambda v: step.add(a=v, b=0))

    out = _flow_to_outputs(run, xs=[7, 8])
    per_item = out["result"] if isinstance(out.get("result"), list) else out["result"]["result"]
    values = [r["result"] if isinstance(r, dict) else r for r in per_item]
    assert values == [7, 8]
