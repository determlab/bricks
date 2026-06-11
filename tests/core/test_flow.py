"""Tests for the @flow decorator and FlowDefinition."""

from __future__ import annotations

from ruamel.yaml import YAML

from bricks.core.dag import DAG
from bricks.core.dsl import FlowDefinition, Node, _tracer, branch, flow, for_each, step
from bricks.core.models import BlueprintDefinition


class TestFlowDecorator:
    """Tests for the @flow decorator itself."""

    def setup_method(self) -> None:
        """Reset tracer before each test."""
        _tracer.stop()
        _tracer.nodes.clear()

    def test_flow_decorator_returns_flow_definition(self) -> None:
        """@flow returns a FlowDefinition, not a callable."""

        @flow
        def my_pipe() -> Node:
            """Simple pipe."""
            return step.noop()

        assert isinstance(my_pipe, FlowDefinition)

    def test_flow_definition_has_name(self) -> None:
        """FlowDefinition.name matches the decorated function's name."""

        @flow
        def my_pipeline() -> Node:
            """My pipeline."""
            return step.noop()

        assert my_pipeline.name == "my_pipeline"

    def test_flow_definition_has_docstring(self) -> None:
        """FlowDefinition.description matches the function docstring."""

        @flow
        def documented_flow() -> Node:
            """This is the description."""
            return step.noop()

        assert documented_flow.description == "This is the description."

    def test_flow_to_dag_returns_dag(self) -> None:
        """to_dag() returns a DAG object."""

        @flow
        def pipe() -> Node:
            """Pipe."""
            return step.clean(text="x")

        dag = pipe.to_dag()
        assert isinstance(dag, DAG)
        assert len(dag.nodes) == 1

    def test_flow_to_blueprint_returns_blueprint_definition(self) -> None:
        """to_blueprint() returns a BlueprintDefinition."""

        @flow
        def pipe() -> Node:
            """Pipe."""
            return step.clean(text="x")

        bp = pipe.to_blueprint()
        assert isinstance(bp, BlueprintDefinition)

    def test_flow_to_yaml_returns_string(self) -> None:
        """to_yaml() returns a non-empty string."""

        @flow
        def pipe() -> Node:
            """Pipe."""
            return step.clean(text="x")

        result = pipe.to_yaml()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_flow_to_yaml_is_valid_yaml(self) -> None:
        """to_yaml() output is parseable YAML."""

        @flow
        def pipe() -> Node:
            """Pipe."""
            return step.clean(text="x")

        result = pipe.to_yaml()
        parsed = YAML(typ="safe").load(result)
        assert isinstance(parsed, dict)


class TestFlowTracing:
    """Tests that @flow traces the correct node structure."""

    def setup_method(self) -> None:
        """Reset tracer before each test."""
        _tracer.stop()
        _tracer.nodes.clear()

    def test_flow_simple_chain(self) -> None:
        """@flow with a 3-step chain traces 3 nodes."""

        @flow
        def pipe(data: object) -> Node:
            """Chain."""
            a = step.load(path=data)
            b = step.clean(text=a)
            return step.save(result=b)

        assert len(pipe.dag.nodes) == 3

    def test_flow_with_for_each(self) -> None:
        """@flow with for_each traces the for_each node."""

        def do_fn(item: object) -> Node:
            """Inner."""
            return step.process(data=item)

        @flow
        def pipe(items: object) -> Node:
            """For-each flow."""
            loaded = step.load(path=items)
            return for_each(items=loaded, do=do_fn)

        types = {n.type for n in pipe.dag.nodes.values()}
        assert "for_each" in types

    def test_flow_with_branch(self) -> None:
        """@flow with branch traces the branch node."""

        def true_fn() -> Node:
            """True branch."""
            return step.approve()

        def false_fn() -> Node:
            """False branch."""
            return step.reject()

        @flow
        def pipe() -> Node:
            """Branch flow."""
            return branch("is_valid", if_true=true_fn, if_false=false_fn)

        types = {n.type for n in pipe.dag.nodes.values()}
        assert "branch" in types

    def test_flow_complex_pipeline(self) -> None:
        """@flow with 5+ steps traces them all."""

        def do_fn(item: object) -> Node:
            """Inner."""
            return step.transform(x=item)

        @flow
        def complex_pipe(data: object) -> Node:
            """Complex pipeline."""
            raw = step.load(path=data)
            validated = step.validate(data=raw)
            processed = for_each(items=validated, do=do_fn)
            aggregated = step.aggregate(results=processed)
            return step.format_output(data=aggregated)

        assert len(complex_pipe.dag.nodes) >= 5

    def test_flow_blueprint_has_correct_step_count(self) -> None:
        """Blueprint step count matches traced node count."""

        @flow
        def pipe() -> Node:
            """Two steps."""
            a = step.load()
            return step.save(data=a)

        bp = pipe.to_blueprint()
        assert len(bp.steps) == len(pipe.dag.nodes)

    def test_flow_blueprint_step_references(self) -> None:
        """Node references in params become ${...} in blueprint steps."""

        @flow
        def pipe() -> Node:
            """Chain with ref."""
            a = step.load(path="x")
            return step.clean(data=a)

        bp = pipe.to_blueprint()
        clean_step = next(s for s in bp.steps if s.brick == "clean")
        assert "${" in str(clean_step.params.get("data", ""))

    def test_flow_no_return_value(self) -> None:
        """Function that doesn't return a Node still creates a FlowDefinition."""

        @flow
        def pipe() -> None:
            """No return."""
            step.load()
            step.save()

        assert isinstance(pipe, FlowDefinition)
        assert len(pipe.dag.nodes) == 2

    def test_flow_empty_function(self) -> None:
        """Function with no step calls creates FlowDefinition with empty DAG."""

        @flow
        def empty_pipe() -> None:
            """Empty."""

        assert isinstance(empty_pipe, FlowDefinition)
        assert len(empty_pipe.dag.nodes) == 0
