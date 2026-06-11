"""Tests for bricks.core.dsl — for_each, branch, ExecutionTracer primitives."""

from __future__ import annotations

import pytest

from bricks.core.dsl import ExecutionTracer, Node, _tracer, branch, for_each, step


class TestForEach:
    """Tests for the for_each() primitive."""

    def test_for_each_creates_node(self) -> None:
        """for_each returns a Node with type='for_each'."""

        def do_fn(item: object) -> Node:
            """Dummy body."""
            return step.clean(text=item)

        node = for_each(items=[1, 2, 3], do=do_fn)
        assert node.type == "for_each"

    def test_for_each_with_node_items(self) -> None:
        """items can be a Node (output of a previous step)."""

        def do_fn(item: object) -> Node:
            """Dummy body."""
            return step.process(data=item)

        items_node = step.load(path="data.csv")
        node = for_each(items=items_node, do=do_fn)
        assert node.items is items_node

    def test_for_each_on_error_default_is_fail(self) -> None:
        """Default on_error for for_each is 'fail'."""

        def do_fn(item: object) -> Node:
            """Dummy body."""
            return step.noop(x=item)

        node = for_each(items=[], do=do_fn)
        assert node.on_error == "fail"

    def test_for_each_on_error_collect(self) -> None:
        """on_error='collect' is accepted."""

        def do_fn(item: object) -> Node:
            """Dummy body."""
            return step.noop(x=item)

        node = for_each(items=[], do=do_fn, on_error="collect")
        assert node.on_error == "collect"

    def test_for_each_on_error_invalid_raises(self) -> None:
        """on_error='skip' raises ValueError."""

        def do_fn(item: object) -> Node:
            """Dummy body."""
            return step.noop(x=item)

        with pytest.raises(ValueError, match="on_error must be"):
            for_each(items=[], do=do_fn, on_error="skip")


class TestBranch:
    """Tests for the branch() primitive."""

    def test_branch_creates_node(self) -> None:
        """branch returns a Node with type='branch' and string condition."""

        def true_fn() -> Node:
            """Dummy true branch."""
            return step.approve()

        def false_fn() -> Node:
            """Dummy false branch."""
            return step.reject()

        node = branch("is_valid", if_true=true_fn, if_false=false_fn)
        assert node.type == "branch"
        assert node.condition == "is_valid"

    def test_branch_condition_must_be_string(self) -> None:
        """Passing a lambda as condition raises TypeError."""

        def true_fn() -> Node:
            """Dummy true branch."""
            return step.approve()

        def false_fn() -> Node:
            """Dummy false branch."""
            return step.reject()

        condition_fn = lambda x: x  # noqa: E731
        with pytest.raises(TypeError, match="condition must be a brick name string"):
            branch(condition_fn, if_true=true_fn, if_false=false_fn)  # type: ignore[arg-type]

    def test_branch_condition_must_be_string_not_int(self) -> None:
        """Passing an int as condition raises TypeError."""

        def true_fn() -> Node:
            """Dummy true branch."""
            return step.approve()

        def false_fn() -> Node:
            """Dummy false branch."""
            return step.reject()

        with pytest.raises(TypeError, match="condition must be a brick name string"):
            branch(42, if_true=true_fn, if_false=false_fn)  # type: ignore[arg-type]


class TestExecutionTracer:
    """Tests for the ExecutionTracer class."""

    def setup_method(self) -> None:
        """Reset module-level tracer before each test."""
        _tracer.stop()
        _tracer.nodes.clear()

    def test_tracer_records_when_active(self) -> None:
        """Active tracer captures nodes."""
        tracer = ExecutionTracer()
        tracer.start()
        n1 = Node(type="brick", brick_name="a")
        n2 = Node(type="brick", brick_name="b")
        tracer.record(n1)
        tracer.record(n2)
        tracer.stop()
        assert len(tracer.get_nodes()) == 2

    def test_tracer_ignores_when_inactive(self) -> None:
        """Inactive tracer does not capture nodes."""
        tracer = ExecutionTracer()
        n = Node(type="brick", brick_name="a")
        tracer.record(n)
        assert tracer.get_nodes() == []

    def test_tracer_start_clears_previous(self) -> None:
        """Calling start() resets the node list."""
        tracer = ExecutionTracer()
        tracer.start()
        tracer.record(Node(type="brick", brick_name="old"))
        tracer.start()  # second start clears
        tracer.record(Node(type="brick", brick_name="new"))
        tracer.stop()
        nodes = tracer.get_nodes()
        assert len(nodes) == 1
        assert nodes[0].brick_name == "new"

    def test_tracer_stop_stops_recording(self) -> None:
        """Nodes created after stop() are not captured."""
        tracer = ExecutionTracer()
        tracer.start()
        tracer.record(Node(type="brick", brick_name="a"))
        tracer.stop()
        tracer.record(Node(type="brick", brick_name="b"))
        assert len(tracer.get_nodes()) == 1

    def test_tracer_get_nodes_returns_copy(self) -> None:
        """Mutating the returned list does not affect the tracer."""
        tracer = ExecutionTracer()
        tracer.start()
        tracer.record(Node(type="brick", brick_name="a"))
        tracer.stop()
        result = tracer.get_nodes()
        result.clear()
        assert len(tracer.get_nodes()) == 1

    def test_step_proxy_records_to_tracer(self) -> None:
        """step.X() calls are captured by the active module-level tracer."""
        _tracer.start()
        step.clean(text="hi")
        step.sort(items=[])
        _tracer.stop()
        nodes = _tracer.get_nodes()
        assert len(nodes) == 2
        assert nodes[0].brick_name == "clean"
        assert nodes[1].brick_name == "sort"

    def test_for_each_records_to_tracer(self) -> None:
        """for_each() calls are captured by the active module-level tracer."""

        def do_fn(item: object) -> Node:
            """Dummy body."""
            return step.process(data=item)

        _tracer.start()
        for_each(items=[1, 2], do=do_fn)
        _tracer.stop()
        nodes = _tracer.get_nodes()
        assert any(n.type == "for_each" for n in nodes)

    def test_branch_records_to_tracer(self) -> None:
        """branch() calls are captured by the active module-level tracer."""

        def true_fn() -> Node:
            """Dummy true branch."""
            return step.approve()

        def false_fn() -> Node:
            """Dummy false branch."""
            return step.reject()

        _tracer.start()
        branch("is_valid", if_true=true_fn, if_false=false_fn)
        _tracer.stop()
        nodes = _tracer.get_nodes()
        assert any(n.type == "branch" for n in nodes)

    def test_nested_for_each_with_branch(self) -> None:
        """Complex: for_each containing branch creates correct node hierarchy."""

        def do_fn(item: object) -> Node:
            """Inner body with branch."""

            def true_fn() -> Node:
                """True branch."""
                return step.process_a(data=item)

            def false_fn() -> Node:
                """False branch."""
                return step.process_b(data=item)

            return branch("check_condition", if_true=true_fn, if_false=false_fn)

        items_node = step.load(path="data.csv")
        node = for_each(items=items_node, do=do_fn)
        assert node.type == "for_each"
        assert node.items is items_node
        # After lambda extraction, do is the brick name string (not the callable)
        assert isinstance(node.do, str)
        assert node.do == "__branch__"
