"""Compiling the same @flow twice gives the same YAML (G2 in docs/DECISIONS.md)."""

from __future__ import annotations

import pytest

from bricks.core.dsl import FlowDefinition, flow, step


def _compile() -> FlowDefinition:
    @flow
    def f():  # type: ignore[no-untyped-def]
        a = step.add(a=1.0, b=2.0)
        b = step.multiply(a=3.0, b=4.0)
        return {"a": a, "b": b}

    assert isinstance(f, FlowDefinition)
    return f


def test_same_flow_compiles_to_one_yaml() -> None:
    texts = {_compile().to_yaml() for _ in range(20)}
    assert len(texts) == 1


def test_steps_follow_written_order() -> None:
    text = _compile().to_yaml()
    assert text.index("step_1_add") < text.index("step_2_multiply")


def test_many_independent_steps_keep_written_order() -> None:
    # More than ten nodes: "10" must not sort before "2".
    @flow
    def g():  # type: ignore[no-untyped-def]
        return {f"k{i}": step.add(a=float(i), b=1.0) for i in range(12)}

    assert isinstance(g, FlowDefinition)
    order = [g.dag.nodes[nid].params["a"] for nid in g.dag.topological_sort()]
    assert order == [float(i) for i in range(12)]


def test_returning_a_step_made_outside_the_flow_raises() -> None:
    pre = step.add(a=9.0, b=9.0)  # id from the global counter, not the trace

    with pytest.raises(ValueError, match="create every step inside the @flow body"):

        @flow
        def h():  # type: ignore[no-untyped-def]
            z = step.multiply(a=1.0, b=1.0)
            return {"pre": pre, "z": z}


def test_returning_a_lone_step_made_outside_the_flow_raises() -> None:
    pre = step.add(a=9.0, b=9.0)

    with pytest.raises(ValueError, match="create every step inside the @flow body"):

        @flow
        def k():  # type: ignore[no-untyped-def]
            step.multiply(a=1.0, b=1.0)
            return pre
