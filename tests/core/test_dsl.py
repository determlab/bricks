"""Tests for bricks.core.dsl — Node and StepProxy data model."""

from __future__ import annotations

import re

import pytest

from bricks.core.dsl import Node, StepProxy, step


class TestStepProxy:
    """Tests for StepProxy and the module-level step singleton."""

    def test_step_proxy_creates_brick_node(self) -> None:
        """step.clean(text='hi') returns Node with correct type, brick_name, params."""
        node = step.clean(text="hi")
        assert node.type == "brick"
        assert node.brick_name == "clean"
        assert node.params == {"text": "hi"}

    def test_step_proxy_different_bricks(self) -> None:
        """step.filter and step.sort create nodes with distinct brick_names."""
        n1 = step.filter(items=[], key="status", value="active")
        n2 = step.sort(items=[], field="name")
        assert n1.brick_name == "filter"
        assert n2.brick_name == "sort"
        assert n1.brick_name != n2.brick_name

    def test_step_proxy_no_positional_args(self) -> None:
        """step.clean('hello') raises TypeError — keyword-only."""
        with pytest.raises(TypeError):
            step.clean("hello")  # type: ignore[call-arg]

    def test_step_proxy_returns_callable(self) -> None:
        """Accessing step.X returns a callable before being called."""
        fn = step.my_brick
        assert callable(fn)

    def test_step_singleton_is_step_proxy(self) -> None:
        """The module-level step is a StepProxy instance."""
        assert isinstance(step, StepProxy)


class TestNode:
    """Tests for the Node dataclass."""

    def test_node_auto_generates_unique_id(self) -> None:
        """Two independently created nodes have different ids."""
        n1 = Node()
        n2 = Node()
        assert n1.id != n2.id

    def test_node_id_is_8_char_hex(self) -> None:
        """Node id is exactly 8 lowercase hex characters."""
        node = Node()
        assert re.fullmatch(r"[0-9a-f]{8}", node.id)

    def test_node_defaults(self) -> None:
        """Fresh Node() has expected default field values."""
        node = Node()
        assert node.type == ""
        assert node.brick_name == ""
        assert node.params == {}
        assert node.depends_on == []
        assert node.items is None
        assert node.do is None
        assert node.condition is None
        assert node.if_true is None
        assert node.if_false is None

    def test_node_on_error_default_is_fail(self) -> None:
        """Node.on_error defaults to 'fail'."""
        node = Node()
        assert node.on_error == "fail"

    def test_node_params_can_reference_other_nodes(self) -> None:
        """step.process(data=step.clean(text='x')) creates nested Node references."""
        inner = step.clean(text="x")
        outer = step.process(data=inner)
        assert isinstance(outer.params["data"], Node)
        assert outer.params["data"].brick_name == "clean"

    def test_node_repr_brick(self) -> None:
        """repr for a brick node shows brick_name and id."""
        node = Node(type="brick", brick_name="my_brick")
        r = repr(node)
        assert "brick='my_brick'" in r
        assert node.id in r

    def test_node_repr_non_brick(self) -> None:
        """repr for a non-brick node shows type and id."""
        node = Node(type="for_each")
        r = repr(node)
        assert "type='for_each'" in r
        assert node.id in r

    def test_node_for_each_fields(self) -> None:
        """Node stores for_each-specific fields correctly."""

        def do_fn(n: Node) -> Node:
            """Dummy for_each body."""
            return step.clean(text=n)

        items_node = step.load(path="data.csv")
        node = Node(type="for_each", items=items_node, do=do_fn, on_error="collect")
        assert node.items is items_node
        assert node.do is do_fn
        assert node.on_error == "collect"

    def test_node_branch_fields(self) -> None:
        """Node stores branch-specific fields correctly."""

        def true_fn() -> Node:
            """Dummy true branch."""
            return step.approve()

        def false_fn() -> Node:
            """Dummy false branch."""
            return step.reject()

        node = Node(type="branch", condition="is_valid", if_true=true_fn, if_false=false_fn)
        assert node.condition == "is_valid"
        assert node.if_true is true_fn
        assert node.if_false is false_fn

    def test_node_depends_on_is_mutable_list(self) -> None:
        """depends_on starts empty and can be appended to without aliasing."""
        n1 = Node()
        n2 = Node()
        n1.depends_on.append("abc")
        assert n2.depends_on == []  # no shared state

    def test_node_output_returns_self(self) -> None:
        """step1.output is step1 — property returns the node itself."""
        step1 = step.brick_a()
        assert step1.output is step1

    def test_node_output_as_param_reference(self) -> None:
        """step2.params['data'] is step1 when passed via step1.output."""
        step1 = step.brick_a()
        step2 = step.brick_b(data=step1.output)
        assert step2.params["data"] is step1

    def test_flow_with_output_chaining_no_error(self) -> None:
        """@flow with .output chaining traces and converts to DAG without AttributeError."""
        from bricks.core.dsl import flow as dsl_flow

        @dsl_flow
        def chained_flow(inp: None) -> None:
            s1 = step.a(x=inp)
            s2 = step.b(y=s1.output)
            return s2

        dag = chained_flow.to_dag()
        assert len(dag.nodes) == 2
        # s2 must depend on s1
        edges_flat = [dep for deps in dag.edges.values() for dep in deps]
        assert len(edges_flat) == 1


class TestFlowDefinitionExecute:
    """Tests for FlowDefinition.execute() with real-input re-tracing."""

    def test_execute_with_kwargs_calls_engine_with_real_params(self) -> None:
        """execute() re-traces _fn with real inputs so step params hold real values."""
        from unittest.mock import MagicMock

        from bricks.core.dsl import flow as dsl_flow
        from bricks.core.models import ExecutionResult

        @dsl_flow
        def my_flow(text: None) -> None:
            """Test flow."""
            return step.my_brick(text=text)

        mock_engine = MagicMock()
        mock_engine.run.return_value = ExecutionResult(outputs={"result": "done"}, steps=[])
        result = my_flow.execute(engine=mock_engine, text="hello")
        assert result == {"result": "done"}
        # Verify the blueprint passed to engine has real param value
        call_bp = mock_engine.run.call_args[0][0]
        assert call_bp.steps[0].params.get("text") == "hello"

    def test_execute_returns_dict(self) -> None:
        """execute() always returns a dict."""
        from unittest.mock import MagicMock

        from bricks.core.dsl import flow as dsl_flow
        from bricks.core.models import ExecutionResult

        @dsl_flow
        def simple_flow(data: None) -> None:
            """Test flow."""
            return step.process(data=data)

        mock_engine = MagicMock()
        mock_engine.run.return_value = ExecutionResult(outputs={"x": 1}, steps=[])
        result = simple_flow.execute(engine=mock_engine, data="test")
        assert isinstance(result, dict)


class TestFlowDictReturn:
    """Tests for @flow dict-return multi-output support (Mission 072 Fix 3)."""

    def test_flow_dict_return_creates_output_nodes(self) -> None:
        """@flow returning dict[str, Node] stores output_nodes on FlowDefinition."""
        from bricks.core.dsl import flow as dsl_flow

        @dsl_flow
        def multi_flow(data: None) -> None:
            a = step.brick_a(x=data)
            b = step.brick_b(y=data)
            return {"out_a": a, "out_b": b}  # type: ignore[return-value]

        assert multi_flow.output_nodes is not None
        assert set(multi_flow.output_nodes.keys()) == {"out_a", "out_b"}
        assert all(isinstance(v, Node) for v in multi_flow.output_nodes.values())

    def test_flow_dict_return_execute_remaps_outputs(self) -> None:
        """execute() with dict-return flow remaps outputs to declared output keys."""
        from typing import cast

        from bricks.core.brick import BrickFunction, brick
        from bricks.core.dsl import flow as dsl_flow
        from bricks.core.engine import BlueprintEngine
        from bricks.core.registry import BrickRegistry

        registry = BrickRegistry()

        @brick(description="Upper case. Returns {result: upper}.")
        def upper_case(text: str) -> dict:  # type: ignore[type-arg]
            """Upper case."""
            return {"result": text.upper()}

        @brick(description="Count chars. Returns {result: count}.")
        def count_chars(text: str) -> dict:  # type: ignore[type-arg]
            """Count chars."""
            return {"result": len(text)}

        for fn in (upper_case, count_chars):
            typed = cast(BrickFunction, fn)
            registry.register(typed.__brick_meta__.name, typed, typed.__brick_meta__)

        @dsl_flow
        def multi_flow(raw_text: None) -> None:
            """Multi-output flow."""
            upper = step.upper_case(text=raw_text)
            count = step.count_chars(text=raw_text)
            return {"uppercased": upper, "char_count": count}  # type: ignore[return-value]

        engine = BlueprintEngine(registry=registry)
        result = multi_flow.execute(engine=engine, raw_text="hello")

        assert "uppercased" in result, f"Expected 'uppercased' in {result}"
        assert "char_count" in result, f"Expected 'char_count' in {result}"
        assert result["uppercased"] == "HELLO"
        assert result["char_count"] == 5

    def test_flow_dict_return_invalid_raises(self) -> None:
        """@flow returning dict with non-Node values raises TypeError at decoration time."""
        import pytest

        from bricks.core.dsl import flow as dsl_flow

        with pytest.raises(TypeError, match="Non-Node values"):

            @dsl_flow
            def bad_flow(data: None) -> None:
                return {"a": "not_a_node"}  # type: ignore[return-value]


class TestFlowCallForm:
    """Tests for @flow(), @flow(kwargs), and bare @flow call forms (Mission 073)."""

    def test_flow_accepts_kwargs(self) -> None:
        """@flow(outputs_map={}) decorates without raising TypeError."""
        from bricks.core.dsl import FlowDefinition
        from bricks.core.dsl import flow as dsl_flow

        @dsl_flow(outputs_map={})
        def my_flow(data: None) -> None:
            return step.some_brick(text=data)

        assert isinstance(my_flow, FlowDefinition)

    def test_flow_accepts_empty_call(self) -> None:
        """@flow() (empty parentheses) decorates without error."""
        from bricks.core.dsl import FlowDefinition
        from bricks.core.dsl import flow as dsl_flow

        @dsl_flow()
        def my_flow(data: None) -> None:
            return step.some_brick(text=data)

        assert isinstance(my_flow, FlowDefinition)

    def test_flow_bare_still_works(self) -> None:
        """Regression: bare @flow still returns FlowDefinition after Mission 073 changes."""
        from bricks.core.dsl import FlowDefinition
        from bricks.core.dsl import flow as dsl_flow

        @dsl_flow
        def my_flow(data: None) -> None:
            return step.some_brick(text=data)

        assert isinstance(my_flow, FlowDefinition)

    def test_flow_dict_return_multi_output(self) -> None:
        """Flow returning dict of Nodes produces all declared output keys with correct values."""
        from typing import cast

        from bricks.core.brick import BrickFunction, brick
        from bricks.core.dsl import FlowDefinition
        from bricks.core.dsl import flow as dsl_flow
        from bricks.core.engine import BlueprintEngine
        from bricks.core.registry import BrickRegistry

        registry = BrickRegistry()

        @brick(description="Double the number. Returns {result: doubled}.")
        def double_num(n: int) -> dict:  # type: ignore[type-arg]
            """Double."""
            return {"result": n * 2}

        @brick(description="Square the number. Returns {result: squared}.")
        def square_num(n: int) -> dict:  # type: ignore[type-arg]
            """Square."""
            return {"result": n * n}

        for fn in (double_num, square_num):
            typed = cast(BrickFunction, fn)
            registry.register(typed.__brick_meta__.name, typed, typed.__brick_meta__)

        @dsl_flow
        def multi_flow(val: None) -> None:
            a = step.double_num(n=val)
            b = step.square_num(n=val)
            return {"doubled": a, "squared": b}  # type: ignore[return-value]

        assert isinstance(multi_flow, FlowDefinition)
        engine = BlueprintEngine(registry=registry)
        result = multi_flow.execute(inputs={"val": 4}, engine=engine)

        assert result["doubled"] == 8, f"Expected 8, got {result['doubled']}"
        assert result["squared"] == 16, f"Expected 16, got {result['squared']}"

    def test_execute_passes_inputs_to_engine(self) -> None:
        """execute(inputs=...) passes the dict to BlueprintEngine.run() so step params resolve."""
        from typing import cast

        from bricks.core.brick import BrickFunction, brick
        from bricks.core.dsl import flow as dsl_flow
        from bricks.core.engine import BlueprintEngine
        from bricks.core.registry import BrickRegistry

        registry = BrickRegistry()

        @brick(description="Echo text. Returns {result: text}.")
        def echo_text(text: str) -> dict:  # type: ignore[type-arg]
            """Echo."""
            return {"result": text}

        typed = cast(BrickFunction, echo_text)
        registry.register(typed.__brick_meta__.name, typed, typed.__brick_meta__)

        @dsl_flow
        def echo_flow(raw_text: None) -> None:
            return step.echo_text(text=raw_text)

        engine = BlueprintEngine(registry=registry)
        result = echo_flow.execute(inputs={"raw_text": "hello world"}, engine=engine)

        assert result.get("result") == "hello world", f"Expected 'hello world', got: {result}"


class TestImports:
    """Tests that public exports work as documented."""

    def test_import_from_bricks(self) -> None:
        """from bricks import step, Node works."""
        from bricks import Node as BricksNode
        from bricks import step as bricks_step

        assert bricks_step is not None
        assert BricksNode is Node

    def test_import_from_bricks_core_dsl(self) -> None:
        """from bricks.core.dsl import Node, StepProxy, step works."""
        from bricks.core.dsl import Node as BricksNode
        from bricks.core.dsl import StepProxy as BricksStepProxy
        from bricks.core.dsl import step as bricks_step

        assert isinstance(bricks_step, BricksStepProxy)
        assert BricksNode is Node


# ── for_each lambda extraction tests (Mission 076) ──────────────────────


class TestForEachLambdaExtraction:
    """Tests for for_each() brick name extraction from lambda."""

    def test_for_each_extracts_brick_name(self) -> None:
        """for_each stores brick name string (not callable) on the Node."""
        from bricks.core.dsl import for_each

        data = step.load(path="data.json")
        node = for_each(items=data, do=lambda item: step.process(data=item))
        assert isinstance(node.do, str), f"Expected string, got {type(node.do)}"
        assert node.do == "process"

    def test_for_each_extracts_with_output_chaining(self) -> None:
        """for_each extraction works when lambda uses .output."""
        from bricks.core.dsl import for_each

        data = step.load(path="data.json")
        node = for_each(items=data, do=lambda item: step.transform(data=item.output))
        assert node.do == "transform"

    def test_for_each_extraction_failure_raises(self) -> None:
        """for_each raises ValueError when lambda doesn't call any brick step."""
        import pytest

        from bricks.core.dsl import for_each

        data = step.load(path="data.json")
        with pytest.raises(ValueError, match="could not extract brick name"):
            for_each(items=data, do=lambda item: item)  # type: ignore[arg-type]

    def test_for_each_preserves_outer_trace(self) -> None:
        """Outer trace nodes are preserved after for_each extraction."""
        from bricks.core.dsl import _tracer, for_each

        _tracer.start()
        a = step.step_a(x="value")
        _ = for_each(items=a, do=lambda item: step.step_b(data=item))
        step.step_c(y="other")
        _tracer.stop()
        nodes = _tracer.get_nodes()
        brick_names = [n.brick_name for n in nodes if n.brick_name]
        assert "step_a" in brick_names
        assert "step_c" in brick_names

    def test_nested_node_param_resolves_via_resolve_param(self) -> None:
        """_resolve_param correctly resolves Nodes nested in lists and dicts."""
        from bricks.core.dag import _resolve_param

        a = step.brick_a(x="val")
        b = step.brick_b(y="val")
        mapping = {a.id: "step_1_brick_a", b.id: "step_2_brick_b"}

        # List containing Nodes
        result = _resolve_param([a, "literal", b], mapping)
        assert result == ["${step_1_brick_a.result}", "literal", "${step_2_brick_b.result}"]

        # Dict containing Nodes
        result2 = _resolve_param({"first": a, "second": b, "const": 42}, mapping)
        assert result2 == {"first": "${step_1_brick_a.result}", "second": "${step_2_brick_b.result}", "const": 42}

    def test_to_blueprint_multi_output_outputs_map(self) -> None:
        """FlowDefinition.to_blueprint() injects outputs_map for dict-return flows."""
        from bricks.core.dsl import flow as dsl_flow

        @dsl_flow
        def multi_flow(data: None) -> None:
            a = step.brick_a(x=data)
            b = step.brick_b(y=data)
            return {"out_a": a, "out_b": b}  # type: ignore[return-value]

        bp = multi_flow.to_blueprint()
        assert "out_a" in bp.outputs_map, f"Missing 'out_a' in {bp.outputs_map}"
        assert "out_b" in bp.outputs_map, f"Missing 'out_b' in {bp.outputs_map}"
        # Values should be ${step_N.result} strings
        for key, val in bp.outputs_map.items():
            assert val.startswith("${"), f"Expected ${...} reference for {key}, got {val}"
