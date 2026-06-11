"""Tests for bricks.core.context."""

import pytest

from bricks.core.context import ExecutionContext


class TestExecutionContext:
    def test_initial_state(self) -> None:
        ctx = ExecutionContext(inputs={"voltage": 5.0})
        assert ctx.inputs == {"voltage": 5.0}, f"Expected {{'voltage': 5.0}}, got {ctx.inputs!r}"
        assert ctx.results == {}, f"Expected {{}}, got {ctx.results!r}"
        assert ctx.step_index == 0, f"Expected 0, got {ctx.step_index!r}"

    def test_save_and_retrieve_result(self) -> None:
        ctx = ExecutionContext()
        ctx.save_result("measured", 4.95)
        assert ctx.results["measured"] == 4.95, f"Expected 4.95, got {ctx.results['measured']!r}"

    def test_get_variable_checks_results_first(self) -> None:
        ctx = ExecutionContext(inputs={"x": 1})
        ctx.save_result("x", 2)
        assert ctx.get_variable("x") == 2, f"Expected 2, got {ctx.get_variable('x')!r}"

    def test_get_variable_missing_raises(self) -> None:
        ctx = ExecutionContext()
        with pytest.raises(KeyError):
            ctx.get_variable("missing")


class TestExecutionContextAdvanced:
    def test_initial_step_index_is_zero(self) -> None:
        ctx = ExecutionContext()
        assert ctx.step_index == 0, f"Expected 0, got {ctx.step_index!r}"

    def test_advance_step_increments(self) -> None:
        ctx = ExecutionContext()
        ctx.advance_step()
        assert ctx.step_index == 1, f"Expected 1, got {ctx.step_index!r}"
        ctx.advance_step()
        assert ctx.step_index == 2, f"Expected 2, got {ctx.step_index!r}"

    def test_inputs_accessible_by_namespace(self) -> None:
        ctx = ExecutionContext(inputs={"x": 42})
        inputs_obj = ctx.get_variable("inputs")
        assert inputs_obj["x"] == 42, f"Expected 42, got {inputs_obj['x']!r}"

    def test_input_key_accessible_directly(self) -> None:
        ctx = ExecutionContext(inputs={"channel": 5})
        assert ctx.get_variable("channel") == 5, f"Expected 5, got {ctx.get_variable('channel')!r}"

    def test_save_result_and_retrieve(self) -> None:
        ctx = ExecutionContext()
        ctx.save_result("my_result", 99)
        assert ctx.get_variable("my_result") == 99, f"Expected 99, got {ctx.get_variable('my_result')!r}"

    def test_get_variable_unknown_raises_key_error(self) -> None:
        ctx = ExecutionContext()
        with pytest.raises(KeyError):
            ctx.get_variable("nonexistent")

    def test_empty_inputs(self) -> None:
        ctx = ExecutionContext(inputs={})
        # inputs namespace still accessible
        inputs = ctx.get_variable("inputs")
        assert inputs == {}, f"Expected {{}}, got {inputs!r}"

    def test_none_inputs_defaults_to_empty(self) -> None:
        ctx = ExecutionContext(inputs=None)
        assert ctx.inputs == {}, f"Expected {{}}, got {ctx.inputs!r}"

    def test_results_start_empty(self) -> None:
        ctx = ExecutionContext(inputs={"a": 1})
        assert ctx.results == {}, f"Expected {{}}, got {ctx.results!r}"

    def test_multiple_results_saved(self) -> None:
        ctx = ExecutionContext()
        ctx.save_result("r1", 10)
        ctx.save_result("r2", 20)
        assert ctx.get_variable("r1") == 10, f"Expected 10, got {ctx.get_variable('r1')!r}"
        assert ctx.get_variable("r2") == 20, f"Expected 20, got {ctx.get_variable('r2')!r}"

    def test_result_overrides_input_with_same_name(self) -> None:
        ctx = ExecutionContext(inputs={"x": 100})
        ctx.save_result("x", 999)
        # results take priority over inputs
        assert ctx.get_variable("x") == 999, f"Expected 999, got {ctx.get_variable('x')!r}"

    def test_advance_step_multiple_times(self) -> None:
        ctx = ExecutionContext()
        for _i in range(5):
            ctx.advance_step()
        assert ctx.step_index == 5, f"Expected 5, got {ctx.step_index!r}"
