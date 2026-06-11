"""Tests for bricks.core.dag and bricks.core.dag_builder."""

from __future__ import annotations

import pytest

from bricks.core.dag import DAG
from bricks.core.dag_builder import DAGBuilder
from bricks.core.dsl import Node, _tracer, branch, for_each, step


def _build(nodes: list[Node], root: Node | None = None) -> DAG:
    """Shortcut: build a DAG from a list of nodes."""
    return DAGBuilder().build(nodes, root=root)


def _traced(*callables: object) -> list[Node]:
    """Run callables with tracer active and return recorded nodes."""
    _tracer.start()
    for fn in callables:
        if callable(fn):
            fn()  # type: ignore[operator]
    _tracer.stop()
    return _tracer.get_nodes()


class TestDAGBuilder:
    """Tests for DAGBuilder.build()."""

    def setup_method(self) -> None:
        """Reset tracer before each test."""
        _tracer.stop()
        _tracer.nodes.clear()

    def test_dag_builder_simple_chain(self) -> None:
        """a → b(data=a) → c(data=b) produces edges b→a and c→b."""
        _tracer.start()
        a = step.load(path="data.csv")
        b = step.clean(data=a)
        c = step.save(data=b)
        _tracer.stop()
        nodes = _tracer.get_nodes()

        dag = _build(nodes)
        assert len(dag.nodes) == 3
        assert a.id in dag.edges[b.id]
        assert b.id in dag.edges[c.id]
        assert dag.edges[a.id] == []

    def test_dag_builder_no_deps(self) -> None:
        """Independent nodes have no edges."""
        _tracer.start()
        a = step.brick_a()
        b = step.brick_b()
        _tracer.stop()
        nodes = _tracer.get_nodes()

        dag = _build(nodes)
        assert dag.edges[a.id] == []
        assert dag.edges[b.id] == []

    def test_dag_builder_for_each_depends_on_items(self) -> None:
        """for_each node depends on its items node."""

        def do_fn(item: object) -> Node:
            """Dummy body."""
            return step.process(data=item)

        _tracer.start()
        data = step.load(path="input.csv")
        fe = for_each(items=data, do=do_fn)
        _tracer.stop()
        nodes = _tracer.get_nodes()

        dag = _build(nodes)
        assert data.id in dag.edges[fe.id]

    def test_dag_builder_detects_nodes_inside_list_kwarg(self) -> None:
        """Node refs nested inside a list param register as dependencies.

        Regression for issue #25: when the LLM emits
        ``step.reduce_sum(values=[a.output, b.output])`` the consumer must
        declare edges on both producers so topological sort orders them
        before the consumer.
        """
        _tracer.start()
        a = step.count_a()
        b = step.count_b()
        total = step.reduce_sum(values=[a, b])
        _tracer.stop()
        nodes = _tracer.get_nodes()

        dag = _build(nodes)
        assert a.id in dag.edges[total.id]
        assert b.id in dag.edges[total.id]

    def test_dag_builder_detects_nodes_inside_dict_kwarg(self) -> None:
        """Node refs nested inside a dict param register as dependencies."""
        _tracer.start()
        a = step.load_a()
        b = step.load_b()
        merged = step.merge(sources={"x": a, "y": b})
        _tracer.stop()
        nodes = _tracer.get_nodes()

        dag = _build(nodes)
        assert a.id in dag.edges[merged.id]
        assert b.id in dag.edges[merged.id]

    def test_dag_to_blueprint_with_list_kwarg_serialises_to_yaml(self) -> None:
        """End-to-end regression: list-of-Nodes kwarg round-trips to YAML.

        Pre-fix this raised ``RepresenterError`` because the consumer's list
        kwarg kept raw ``Node`` objects through blueprint_to_yaml.
        """
        from bricks.core.utils import blueprint_to_yaml

        _tracer.start()
        a = step.count_a()
        b = step.count_b()
        step.reduce_sum(values=[a, b])
        _tracer.stop()
        nodes = _tracer.get_nodes()

        dag = _build(nodes)
        blueprint = dag.to_blueprint()
        yaml_text = blueprint_to_yaml(blueprint)

        # Both producer refs must appear as ${...result} strings in the YAML.
        assert yaml_text.count(".result}") >= 2
        assert "Node(" not in yaml_text

    def test_dag_builder_root_is_last_node(self) -> None:
        """root_id defaults to the last node in the list."""
        _tracer.start()
        step.a()
        b = step.b()
        _tracer.stop()
        nodes = _tracer.get_nodes()

        dag = _build(nodes)
        assert dag.root_id == b.id

    def test_dag_builder_explicit_root(self) -> None:
        """Passing root= overrides the default."""
        _tracer.start()
        a = step.a()
        step.b()
        _tracer.stop()
        nodes = _tracer.get_nodes()

        dag = _build(nodes, root=a)
        assert dag.root_id == a.id


class TestTopologicalSort:
    """Tests for DAG.topological_sort()."""

    def test_topological_sort_simple_chain(self) -> None:
        """a → b → c sorts to [a, b, c]."""
        a = Node(type="brick", brick_name="a")
        b = Node(type="brick", brick_name="b")
        c = Node(type="brick", brick_name="c")
        dag = DAG(
            nodes={a.id: a, b.id: b, c.id: c},
            edges={a.id: [], b.id: [a.id], c.id: [b.id]},
        )
        order = dag.topological_sort()
        assert order.index(a.id) < order.index(b.id) < order.index(c.id)

    def test_topological_sort_independent_nodes(self) -> None:
        """Independent nodes all appear in result (deterministic order)."""
        a = Node(type="brick", brick_name="a")
        b = Node(type="brick", brick_name="b")
        dag = DAG(
            nodes={a.id: a, b.id: b},
            edges={a.id: [], b.id: []},
        )
        order = dag.topological_sort()
        assert set(order) == {a.id, b.id}
        assert len(order) == 2

    def test_topological_sort_diamond(self) -> None:
        """Diamond a→b, a→c, b→d, c→d: a first, d last."""
        a = Node(type="brick", brick_name="a")
        b = Node(type="brick", brick_name="b")
        c = Node(type="brick", brick_name="c")
        d = Node(type="brick", brick_name="d")
        dag = DAG(
            nodes={a.id: a, b.id: b, c.id: c, d.id: d},
            edges={a.id: [], b.id: [a.id], c.id: [a.id], d.id: [b.id, c.id]},
        )
        order = dag.topological_sort()
        assert order[0] == a.id
        assert order[-1] == d.id

    def test_topological_sort_cycle_raises(self) -> None:
        """A cycle raises ValueError."""
        a = Node(type="brick", brick_name="a")
        b = Node(type="brick", brick_name="b")
        dag = DAG(
            nodes={a.id: a, b.id: b},
            edges={a.id: [b.id], b.id: [a.id]},
        )
        with pytest.raises(ValueError, match="cycle"):
            dag.topological_sort()


class TestToBlueprint:
    """Tests for DAG.to_blueprint()."""

    def setup_method(self) -> None:
        """Reset tracer before each test."""
        _tracer.stop()
        _tracer.nodes.clear()

    def test_to_blueprint_simple_chain(self) -> None:
        """3-step chain produces a BlueprintDefinition with 3 steps."""
        _tracer.start()
        a = step.load(path="data.csv")
        b = step.clean(data=a)
        step.save(data=b)
        _tracer.stop()
        dag = _build(_tracer.get_nodes())

        bp = dag.to_blueprint(name="my_pipe")
        assert bp.name == "my_pipe"
        assert len(bp.steps) == 3

    def test_to_blueprint_params_resolve_to_refs(self) -> None:
        """Node references in params become ${step_name.result} strings."""
        _tracer.start()
        a = step.load(path="data.csv")
        step.clean(data=a)
        _tracer.stop()
        dag = _build(_tracer.get_nodes())

        bp = dag.to_blueprint()
        clean_step = next(s for s in bp.steps if s.brick == "clean")
        assert "${" in clean_step.params["data"]
        assert ".result}" in clean_step.params["data"]

    def test_to_blueprint_for_each_becomes_builtin(self) -> None:
        """for_each node maps to __for_each__ brick."""

        def do_fn(item: object) -> Node:
            """Dummy body."""
            return step.process(data=item)

        _tracer.start()
        data = step.load(path="x.csv")
        for_each(items=data, do=do_fn)
        _tracer.stop()
        dag = _build(_tracer.get_nodes())

        bp = dag.to_blueprint()
        fe_step = next(s for s in bp.steps if s.brick == "__for_each__")
        assert fe_step is not None

    def test_to_blueprint_branch_becomes_builtin(self) -> None:
        """branch node maps to __branch__ brick."""

        def true_fn() -> Node:
            """True branch."""
            return step.approve()

        def false_fn() -> Node:
            """False branch."""
            return step.reject()

        _tracer.start()
        branch("is_valid", if_true=true_fn, if_false=false_fn)
        _tracer.stop()
        dag = _build(_tracer.get_nodes())

        bp = dag.to_blueprint()
        br_step = next(s for s in bp.steps if s.brick == "__branch__")
        assert br_step.params["condition_brick"] == "is_valid"

    def test_to_blueprint_name_and_description(self) -> None:
        """Custom name and description flow through to BlueprintDefinition."""
        _tracer.start()
        step.noop()
        _tracer.stop()
        dag = _build(_tracer.get_nodes())

        bp = dag.to_blueprint(name="custom", description="my desc")
        assert bp.name == "custom"
        assert bp.description == "my desc"


class TestDAGAccessors:
    """Tests for DAG.get_node() and DAG.get_dependencies()."""

    def test_dag_get_node(self) -> None:
        """get_node returns the correct node."""
        n = Node(type="brick", brick_name="my_brick")
        dag = DAG(nodes={n.id: n}, edges={n.id: []})
        assert dag.get_node(n.id) is n

    def test_dag_get_dependencies(self) -> None:
        """get_dependencies returns the correct dependency nodes."""
        a = Node(type="brick", brick_name="a")
        b = Node(type="brick", brick_name="b")
        dag = DAG(
            nodes={a.id: a, b.id: b},
            edges={a.id: [], b.id: [a.id]},
        )
        deps = dag.get_dependencies(b.id)
        assert len(deps) == 1
        assert deps[0] is a


# ── _resolve_param tests ──────────────────────────────────────────────────


class TestResolveParam:
    """Tests for _resolve_param recursive Node resolution."""

    def test_resolve_param_direct_node(self) -> None:
        """Direct Node is resolved to ${step_name.result} string."""
        from bricks.core.dag import _resolve_param

        node = Node(type="brick", brick_name="foo")
        mapping = {node.id: "step_1_foo"}
        assert _resolve_param(node, mapping) == "${step_1_foo.result}"

    def test_resolve_param_nested_list(self) -> None:
        """Nodes inside a list are resolved."""
        from bricks.core.dag import _resolve_param

        a = Node(type="brick", brick_name="a")
        b = Node(type="brick", brick_name="b")
        mapping = {a.id: "step_1_a", b.id: "step_2_b"}
        result = _resolve_param([a, "literal", b], mapping)
        assert result == ["${step_1_a.result}", "literal", "${step_2_b.result}"]

    def test_resolve_param_nested_dict(self) -> None:
        """Nodes inside a dict are resolved."""
        from bricks.core.dag import _resolve_param

        node = Node(type="brick", brick_name="x")
        mapping = {node.id: "step_1_x"}
        result = _resolve_param({"key": node, "scalar": 42}, mapping)
        assert result == {"key": "${step_1_x.result}", "scalar": 42}

    def test_resolve_param_unknown_node_passthrough(self) -> None:
        """Node not in mapping is returned as-is (defensive fallback)."""
        from bricks.core.dag import _resolve_param

        node = Node(type="brick", brick_name="orphan")
        result = _resolve_param(node, {})
        assert result is node

    def test_resolve_param_scalar_passthrough(self) -> None:
        """Scalar values pass through unchanged."""
        from bricks.core.dag import _resolve_param

        assert _resolve_param("hello", {}) == "hello"
        assert _resolve_param(42, {}) == 42
        assert _resolve_param(None, {}) is None

    def test_for_each_root_generates_outputs_map(self) -> None:
        """DAG whose root is a for_each node produces non-empty outputs_map."""
        _tracer.start()
        data = step.load(path="data.json")
        result = for_each(items=data, do=lambda item: step.process(data=item))
        _tracer.stop()
        dag = _build(_tracer.get_nodes(), root=result)
        bp = dag.to_blueprint()
        assert bp.outputs_map, "for_each root should produce non-empty outputs_map"
        assert "result" in bp.outputs_map

    def setup_method(self) -> None:
        """Reset tracer before each test."""
        _tracer.stop()
        _tracer.nodes.clear()
