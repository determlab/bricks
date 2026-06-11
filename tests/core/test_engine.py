"""Tests for bricks.core.engine."""

from __future__ import annotations

from typing import cast

import pytest

from bricks.core.brick import BrickFunction, brick
from bricks.core.engine import BlueprintEngine
from bricks.core.exceptions import BrickExecutionError
from bricks.core.models import BlueprintDefinition, StepDefinition
from bricks.core.registry import BrickRegistry


class TestBlueprintEngine:
    def test_engine_creation(self) -> None:
        reg = BrickRegistry()
        engine = BlueprintEngine(registry=reg)
        assert engine is not None, "Expected non-None BlueprintEngine"


class TestEngineRun:
    def test_single_step_with_literal_params(self, math_registry: BrickRegistry) -> None:
        engine = BlueprintEngine(registry=math_registry)
        bp = BlueprintDefinition(
            name="test",
            steps=[StepDefinition(name="s1", brick="add", params={"a": 3.0, "b": 4.0}, save_as="total")],
            outputs_map={"result": "${total}"},
        )
        out = engine.run(bp).outputs
        assert out["result"] == 7.0, f"Expected 7.0, got {out['result']!r}"

    def test_empty_outputs_map_returns_empty(self, math_registry: BrickRegistry) -> None:
        engine = BlueprintEngine(registry=math_registry)
        bp = BlueprintDefinition(
            name="test",
            steps=[StepDefinition(name="s1", brick="add", params={"a": 1.0, "b": 2.0})],
        )
        out = engine.run(bp).outputs
        assert out == {}, f"Expected {{}}, got {out!r}"

    def test_inputs_resolved_in_params(self, math_registry: BrickRegistry) -> None:
        engine = BlueprintEngine(registry=math_registry)
        bp = BlueprintDefinition(
            name="test",
            inputs={"x": "float", "y": "float"},
            steps=[
                StepDefinition(
                    name="s1",
                    brick="add",
                    params={"a": "${inputs.x}", "b": "${inputs.y}"},
                    save_as="sum",
                )
            ],
            outputs_map={"total": "${sum}"},
        )
        out = engine.run(bp, inputs={"x": 10.0, "y": 5.0}).outputs
        assert out["total"] == 15.0, f"Expected 15.0, got {out['total']!r}"

    def test_chained_steps(self, math_registry: BrickRegistry) -> None:
        engine = BlueprintEngine(registry=math_registry)
        bp = BlueprintDefinition(
            name="chain",
            steps=[
                StepDefinition(name="s1", brick="add", params={"a": 2.0, "b": 3.0}, save_as="first"),
                StepDefinition(
                    name="s2",
                    brick="multiply",
                    params={"a": "${first}", "b": 2.0},
                    save_as="second",
                ),
            ],
            outputs_map={"result": "${second}"},
        )
        out = engine.run(bp).outputs
        assert out["result"] == 10.0, f"Expected 10.0, got {out['result']!r}"  # (2+3)*2

    def test_brick_exception_wrapped(self) -> None:
        reg = BrickRegistry()

        @brick()
        def broken(x: int) -> int:
            raise ValueError("intentional")

        reg.register("broken", cast(BrickFunction, broken), cast(BrickFunction, broken).__brick_meta__)
        engine = BlueprintEngine(registry=reg)
        bp = BlueprintDefinition(
            name="test",
            steps=[StepDefinition(name="s1", brick="broken", params={"x": 1})],
        )
        with pytest.raises(BrickExecutionError) as exc_info:
            engine.run(bp)
        error_msg = str(exc_info.value)
        assert "broken" in error_msg, f"Expected brick name 'broken' in {error_msg!r}"
        assert "s1" in error_msg, f"Expected step name 's1' in {error_msg!r}"

    def test_none_inputs_treated_as_empty(self, math_registry: BrickRegistry) -> None:
        engine = BlueprintEngine(registry=math_registry)
        bp = BlueprintDefinition(
            name="test",
            steps=[StepDefinition(name="s1", brick="add", params={"a": 1.0, "b": 2.0}, save_as="r")],
            outputs_map={"result": "${r}"},
        )
        out = engine.run(bp, inputs=None).outputs
        assert out["result"] == 3.0, f"Expected 3.0, got {out['result']!r}"

    def test_step_without_save_as_result_not_accessible(self, math_registry: BrickRegistry) -> None:
        engine = BlueprintEngine(registry=math_registry)
        bp = BlueprintDefinition(
            name="test",
            steps=[
                # first step saves nothing
                StepDefinition(name="s1", brick="add", params={"a": 1.0, "b": 2.0}),
                # second step saves result
                StepDefinition(name="s2", brick="add", params={"a": 5.0, "b": 5.0}, save_as="r"),
            ],
            outputs_map={"result": "${r}"},
        )
        out = engine.run(bp).outputs
        assert out["result"] == 10.0, f"Expected 10.0, got {out['result']!r}"

    def test_multiple_outputs(self, math_registry: BrickRegistry) -> None:
        engine = BlueprintEngine(registry=math_registry)
        bp = BlueprintDefinition(
            name="test",
            steps=[
                StepDefinition(name="s1", brick="add", params={"a": 3.0, "b": 4.0}, save_as="sum"),
                StepDefinition(
                    name="s2",
                    brick="multiply",
                    params={"a": 3.0, "b": 4.0},
                    save_as="product",
                ),
            ],
            outputs_map={"sum": "${sum}", "product": "${product}"},
        )
        out = engine.run(bp).outputs
        assert out["sum"] == 7.0, f"Expected 7.0, got {out['sum']!r}"
        assert out["product"] == 12.0, f"Expected 12.0, got {out['product']!r}"

    def test_execution_error_has_correct_attributes(self) -> None:
        reg = BrickRegistry()

        @brick()
        def fails(x: int) -> int:
            raise RuntimeError("fail!")

        reg.register("fails", cast(BrickFunction, fails), cast(BrickFunction, fails).__brick_meta__)
        engine = BlueprintEngine(registry=reg)
        bp = BlueprintDefinition(
            name="test",
            steps=[StepDefinition(name="my_step", brick="fails", params={"x": 1})],
        )
        with pytest.raises(BrickExecutionError) as exc_info:
            engine.run(bp)
        err = exc_info.value
        assert err.brick_name == "fails", f"Expected 'fails', got {err.brick_name!r}"
        assert err.step_name == "my_step", f"Expected 'my_step', got {err.step_name!r}"
        assert isinstance(err.cause, RuntimeError), f"Expected RuntimeError, got {type(err.cause).__name__}"
