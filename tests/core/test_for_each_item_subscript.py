"""Tests for issue #69 — ``for_each`` lambdas may subscript / attr-access the item.

Pre-fix the trace-time mock injected as the iteration item was a plain
:class:`Node`, so the very common composer pattern
``do=lambda pat: step.X(value=pat["pattern"])`` raised
``TypeError: 'Node' object is not subscriptable`` *before* reaching the
inner ``step.X(...)`` call. The tracer recorded zero inner nodes and
the extractor failed with "could not extract brick name from do=
callable" — blocking every list-of-dicts task in RA's Track-1
benchmarks.

The fix introduces :class:`~bricks.core.dsl._ItemProxy`, threads an
``item_paths`` access-path map through the for_each Node, and teaches
the runtime ``__for_each__`` builtin to replay the recorded path on
each real item. This suite locks down the surface end-to-end plus the
issue's acceptance criteria.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from bricks.core.builtins import register_builtins
from bricks.core.dsl import FlowDefinition, _ItemProxy, flow, for_each, step
from bricks.core.engine import BlueprintEngine
from bricks.core.models import BrickMeta
from bricks.core.registry import BrickRegistry


def _make_registry() -> BrickRegistry:
    """Build a registry with a few small bricks + the for_each builtin.

    Mirrors :func:`tests.core.test_for_each_static_kwargs._make_registry`
    so anyone reading both files sees the same shape — but kept local
    so the suites don't import each other.
    """
    reg = BrickRegistry()
    register_builtins(reg)

    def identity(value: Any) -> dict[str, Any]:
        return {"result": value}

    reg.register("identity", identity, BrickMeta(name="identity", description="echo"))

    def add(a: int, b: int) -> dict[str, int]:
        return {"result": a + b}

    reg.register("add", add, BrickMeta(name="add", description="a+b"))

    def filter_dict_list(items: list[dict[str, Any]], key: str, value: Any) -> dict[str, Any]:
        return {"result": [r for r in items if r.get(key) == value]}

    reg.register(
        "filter_dict_list",
        filter_dict_list,
        BrickMeta(name="filter_dict_list", description="filter by key=value"),
    )

    return reg


def _flow_to_outputs(fn: Any, **inputs: Any) -> dict[str, Any]:
    """Compile + run a ``@flow`` decorator'd function through the real engine."""
    flow_def: FlowDefinition = fn  # type: ignore[assignment]
    engine = BlueprintEngine(registry=_make_registry())
    return flow_def.execute(inputs=inputs, engine=engine)


def _per_item_results(out: dict[str, Any]) -> list[Any]:
    """Pull the per-iteration result list out of the flow's output dict.

    Single-output flows surface the for_each output as ``{"result": [...]}``
    where each entry is the inner brick's ``{"result": value}`` dict.
    """
    raw = out["result"]
    items = raw if isinstance(raw, list) else raw["result"]
    return [r["result"] if isinstance(r, dict) and "result" in r else r for r in items]


# --- acceptance criteria from issue #69 -------------------------------------


def test_subscript_extracts_and_runs_end_to_end() -> None:
    """``lambda r: step.identity(value=r["k"])`` — the issue's minimal repro.

    Pre-fix: ValueError from the extractor before reaching the brick.
    Post-fix: each iteration calls ``identity(value=row["k"])``.
    """

    @flow
    def pluck(rows):  # type: ignore[no-untyped-def]
        return for_each(items=rows, do=lambda r: step.identity(value=r["k"]))

    out = _flow_to_outputs(pluck, rows=[{"k": 1}, {"k": 2}, {"k": 3}])
    assert _per_item_results(out) == [1, 2, 3]


def test_attr_access_extracts_and_runs_end_to_end() -> None:
    """Acceptance #2 — attribute-style item access works the same way."""

    @flow
    def pluck_attr(items):  # type: ignore[no-untyped-def]
        return for_each(items=items, do=lambda r: step.identity(value=r.field))

    items = [SimpleNamespace(field=10), SimpleNamespace(field=20)]
    out = _flow_to_outputs(pluck_attr, items=items)
    assert _per_item_results(out) == [10, 20]


def test_chained_subscript_runs_end_to_end() -> None:
    """``r["a"]["b"]`` — nested dicts. Path replay must compose."""

    @flow
    def deep(rows):  # type: ignore[no-untyped-def]
        return for_each(items=rows, do=lambda r: step.identity(value=r["a"]["b"]))

    out = _flow_to_outputs(deep, rows=[{"a": {"b": 7}}, {"a": {"b": 11}}])
    assert _per_item_results(out) == [7, 11]


def test_mixed_path_kwargs_run_independently() -> None:
    """Two derived kwargs from the same item — both paths apply per iteration.

    No whole-item kwarg here; ``item_kwarg`` stays empty so no stray
    ``item=`` injection clashes with the inner brick signature.
    """

    @flow
    def add_pairs(rows):  # type: ignore[no-untyped-def]
        return for_each(items=rows, do=lambda r: step.add(a=r["k"], b=r["v"]))

    rows = [{"k": 1, "v": 10}, {"k": 2, "v": 20}, {"k": 3, "v": 30}]
    out = _flow_to_outputs(add_pairs, rows=rows)
    assert _per_item_results(out) == [11, 22, 33]


def test_composer_emitted_shape_regression_69() -> None:
    """Regression for the bench-runs composer pattern in the issue body.

    ``for_each(items=patterns, do=lambda pat: step.filter_dict_list(items=rows, key="pattern", value=pat["pattern"]))``
    Items closed over as a literal list because lambdas-referencing-other-
    nodes is out of scope (issue's non-goals, same as #61). The shape
    that mattered — ``value=pat["pattern"]`` — is exercised end-to-end.
    """
    rows = [
        {"pattern": "a", "msg": "alpha-1"},
        {"pattern": "b", "msg": "bravo-1"},
        {"pattern": "a", "msg": "alpha-2"},
    ]

    @flow
    def filter_per_pattern(patterns):  # type: ignore[no-untyped-def]
        return for_each(
            items=patterns,
            do=lambda pat: step.filter_dict_list(items=rows, key="pattern", value=pat["pattern"]),
        )

    out = _flow_to_outputs(filter_per_pattern, patterns=[{"pattern": "a"}, {"pattern": "b"}])
    per_item = _per_item_results(out)
    assert per_item == [
        [{"pattern": "a", "msg": "alpha-1"}, {"pattern": "a", "msg": "alpha-2"}],
        [{"pattern": "b", "msg": "bravo-1"}],
    ]


def test_truly_empty_lambda_still_raises_with_60_hints() -> None:
    """Acceptance #5 — a lambda that genuinely never calls ``step.X(...)``
    must still raise the issue-#60 ValueError with the lambda source +
    inner-exception hints. The proxy fix MUST NOT mask diagnostic
    information for the real "no inner step" failure mode."""
    with pytest.raises(ValueError) as exc_info:
        for_each(items=[1, 2, 3], do=lambda _r: None)

    msg = str(exc_info.value)
    assert "could not extract brick name" in msg
    assert "lambda _r: None" in msg


# --- _ItemProxy unit --------------------------------------------------------


def test_item_proxy_records_access_path() -> None:
    """Wire-shape contract for the proxy: subscripts + getattrs build
    a ``[(op, key), ...]`` chain in the order they were applied."""
    p = _ItemProxy(root_id="abc")
    descendant = p["a"].b["c"]
    assert descendant._access_path == [
        ("getitem", "a"),
        ("getattr", "b"),
        ("getitem", "c"),
    ]
    # Every descendant shares the root id so the existing identity
    # check (``value.id == mock.id``) recognises them.
    assert descendant.id == p.id == "abc"
