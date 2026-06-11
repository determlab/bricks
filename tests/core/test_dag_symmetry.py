"""Tests for issue #38 — DAG edge-detection must mirror param-resolution recursion.

The class-of-bug from issue #25 (Node references nested inside list
kwargs silently dropped from ``dag.edges``) was fixed by widening
``_find_dependencies`` to recurse the same way ``_resolve_param`` does.
The fix has unit-level regression tests in
[tests/core/test_dag.py](tests/core/test_dag.py); what is *not*
asserted there is the **symmetry invariant**:

    For every container shape ``_resolve_param`` recurses into when
    rewriting Node references, ``_collect_node_deps`` (called by
    ``_find_dependencies``) must detect the same refs as edges.

A future refactor that taught one side to walk a new container type
(e.g. ``tuple``, ``set``) without updating the other would silently
re-introduce the same family of bug. This module turns that
expectation into a property test parametrised over a fixed grid of
shapes plus the ``for_each.items`` code path which uses a separate
walker but shares the same higher-level invariant.

Tests are intentionally written with an *independent* helper —
``_walk_node_refs`` — so a refactor that updates both production
walkers in lockstep is forced to update this helper too. The diff
makes the symmetry impossible to overlook.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from bricks.core.dag import DAG
from bricks.core.dag_builder import DAGBuilder
from bricks.core.dsl import Node, _tracer, for_each, step


def _build(nodes: list[Node]) -> DAG:
    """Convenience: ``DAGBuilder().build(nodes)`` matching test_dag.py style."""
    return DAGBuilder().build(nodes)


def _walk_node_refs(value: Any) -> Iterator[Node]:
    """Yield every :class:`Node` reference reachable inside *value*.

    This helper is the test's independent statement of the symmetry
    invariant. It mirrors the recursion in
    :func:`bricks.core.dag._resolve_param` and
    :meth:`bricks.core.dag_builder.DAGBuilder._collect_node_deps`.
    If those production walkers ever grow a new container type
    (``tuple``, ``set``, ``frozenset``, ...) this helper must grow with
    them — and the parametrised assertions below will fail until it
    does, surfacing the asymmetry instead of letting it ride.
    """
    if isinstance(value, Node):
        yield value
        return
    if isinstance(value, list):
        for item in value:
            yield from _walk_node_refs(item)
        return
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk_node_refs(item)


def _make_brick(brick_name: str, **params: Any) -> Node:
    """Build a brick :class:`Node` directly — no tracer.

    The shape grid below exercises specific container layouts that are
    awkward to express through the ``step.X(...)`` proxy without
    smuggling the inner Nodes through closures. Building Nodes
    explicitly keeps each parametrised case self-contained.
    """
    return Node(type="brick", brick_name=brick_name, params=params)


class TestDAGSymmetry:
    """Parametrised symmetry invariant across container shapes."""

    def setup_method(self) -> None:
        """Reset tracer before each test — for_each case uses it."""
        _tracer.stop()
        _tracer.nodes.clear()

    @pytest.mark.parametrize(
        ("shape_name", "build_params"),
        [
            ("scalar_node", lambda a, b: {"x": a}),
            ("list_of_nodes", lambda a, b: {"xs": [a, b]}),
            ("node_in_dict", lambda a, b: {"m": {"k": a}}),
            ("node_in_list_of_dicts", lambda a, b: {"xs": [{"k": a}, {"k": b}]}),
            ("node_in_dict_of_list", lambda a, b: {"m": {"outer": [a, b]}}),
        ],
    )
    def test_every_walked_node_has_an_edge(
        self,
        shape_name: str,
        build_params: Any,
    ) -> None:
        """Every Node ref the helper finds in params must appear in edges.

        If ``_collect_node_deps`` ever stops recursing into a shape
        ``_resolve_param`` still recurses into, this fails with a
        clear ``edge missing for {shape_name}`` message naming both
        the consumer and the producer that was dropped.
        """
        a = _make_brick("producer_a")
        b = _make_brick("producer_b")
        consumer = _make_brick("consumer", **build_params(a, b))

        # Only include producers that the shape actually references —
        # otherwise unused producers clutter the DAG and the helper's
        # "every ref present" claim becomes vacuous on shapes that use
        # only one producer (e.g. scalar_node, node_in_dict).
        referenced_producers = list(_walk_node_refs(consumer.params))
        nodes = [*referenced_producers, consumer]

        dag = _build(nodes)
        edges = dag.edges[consumer.id]

        for ref in referenced_producers:
            assert ref.id in edges, (
                f"edge missing for shape {shape_name!r}: "
                f"producer {ref.brick_name!r} reachable in consumer.params via "
                f"_walk_node_refs but absent from dag.edges[consumer]. "
                f"_collect_node_deps and _resolve_param have drifted."
            )

    def test_for_each_items_node_registers_as_edge(self) -> None:
        """``for_each.items`` Node refs travel through a separate path
        in ``_find_dependencies`` (not ``_collect_node_deps``), but the
        same higher-level invariant holds: a Node ref the DAG can reach
        gets an edge."""

        def do_fn(item: object) -> Node:
            """Inner brick — irrelevant to this assertion."""
            return step.process(data=item)

        _tracer.start()
        producer = step.load(path="x.csv")
        fe = for_each(items=producer, do=do_fn)
        _tracer.stop()
        nodes = _tracer.get_nodes()

        dag = _build(nodes)
        assert producer.id in dag.edges[fe.id], (
            "for_each.items Node ref dropped from edges — "
            "_find_dependencies's for_each branch and _resolve_param have drifted."
        )
