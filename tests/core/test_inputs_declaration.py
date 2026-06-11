"""Tests for Blueprint inputs declaration, validation, and execution."""

from __future__ import annotations

from typing import cast

import pytest

from bricks.core.brick import BrickFunction, brick
from bricks.core.engine import BlueprintEngine
from bricks.core.models import BlueprintDefinition, StepDefinition
from bricks.core.registry import BrickRegistry
from bricks.core.validation import BlueprintValidator


@pytest.fixture()
def _add_registry() -> BrickRegistry:
    """Registry with an add brick for inputs tests."""
    reg = BrickRegistry()

    @brick(description="Add two numbers. Returns {result: float}.")
    def add(a: float, b: float) -> float:
        return a + b

    typed = cast(BrickFunction, add)
    reg.register(typed.__brick_meta__.name, typed, typed.__brick_meta__)
    return reg


class TestBlueprintDefinitionInputs:
    """Tests for BlueprintDefinition.inputs accepting Any values."""

    def test_inputs_accepts_float(self) -> None:
        """Inputs dict can hold float values."""
        bp = BlueprintDefinition(name="test", inputs={"width": 7.5})
        assert bp.inputs["width"] == 7.5

    def test_inputs_accepts_int(self) -> None:
        """Inputs dict can hold int values."""
        bp = BlueprintDefinition(name="test", inputs={"count": 3})
        assert bp.inputs["count"] == 3

    def test_inputs_accepts_string(self) -> None:
        """Inputs dict can hold string values."""
        bp = BlueprintDefinition(name="test", inputs={"label": "hello"})
        assert bp.inputs["label"] == "hello"

    def test_inputs_accepts_mixed(self) -> None:
        """Inputs dict can hold mixed types."""
        bp = BlueprintDefinition(
            name="test",
            inputs={"width": 7.5, "count": 3, "label": "hello"},
        )
        assert isinstance(bp.inputs["width"], float)
        assert isinstance(bp.inputs["count"], int)
        assert isinstance(bp.inputs["label"], str)

    def test_inputs_default_empty(self) -> None:
        """Inputs default to empty dict."""
        bp = BlueprintDefinition(name="test")
        assert bp.inputs == {}


class TestValidatorWithDeclaredInputs:
    """Tests for BlueprintValidator passing when ${inputs.X} matches declared inputs."""

    def test_declared_inputs_pass_validation(self, _add_registry: BrickRegistry) -> None:
        """${inputs.X} references pass when X is declared in inputs."""
        bp = BlueprintDefinition(
            name="test",
            inputs={"a": 3.0, "b": 4.0},
            steps=[
                StepDefinition(
                    name="add_step",
                    brick="add",
                    params={"a": "${inputs.a}", "b": "${inputs.b}"},
                    save_as="result",
                ),
            ],
            outputs_map={"sum": "${result.result}"},
        )
        validator = BlueprintValidator(registry=_add_registry)
        validator.validate(bp)  # should not raise

    def test_undeclared_inputs_fail_validation(self, _add_registry: BrickRegistry) -> None:
        """${inputs.X} references fail when X is not in inputs."""
        bp = BlueprintDefinition(
            name="test",
            inputs={},
            steps=[
                StepDefinition(
                    name="add_step",
                    brick="add",
                    params={"a": "${inputs.a}", "b": "${inputs.b}"},
                    save_as="result",
                ),
            ],
            outputs_map={"sum": "${result.result}"},
        )
        validator = BlueprintValidator(registry=_add_registry)
        from bricks.core.exceptions import BlueprintValidationError

        with pytest.raises(BlueprintValidationError) as exc_info:
            validator.validate(bp)
        assert any("not declared" in e for e in exc_info.value.errors)


class TestEngineWithDeclaredInputs:
    """Tests for BlueprintEngine resolving ${inputs.X} with declared inputs."""

    def test_engine_resolves_inputs(self, _add_registry: BrickRegistry) -> None:
        """Engine resolves ${inputs.X} references from declared inputs."""
        bp = BlueprintDefinition(
            name="test",
            inputs={"a": 3.0, "b": 4.0},
            steps=[
                StepDefinition(
                    name="add_step",
                    brick="add",
                    params={"a": "${inputs.a}", "b": "${inputs.b}"},
                    save_as="result",
                ),
            ],
            outputs_map={"sum": "${result}"},
        )
        engine = BlueprintEngine(registry=_add_registry)
        exec_result = engine.run(bp, inputs=bp.inputs)
        assert exec_result.outputs["sum"] == pytest.approx(7.0)

    def test_engine_resolves_mixed_literal_and_inputs(self, _add_registry: BrickRegistry) -> None:
        """Engine handles mix of literal values and ${inputs.X} references."""
        bp = BlueprintDefinition(
            name="test",
            inputs={"a": 10.0},
            steps=[
                StepDefinition(
                    name="add_step",
                    brick="add",
                    params={"a": "${inputs.a}", "b": 5.0},
                    save_as="result",
                ),
            ],
            outputs_map={"sum": "${result}"},
        )
        engine = BlueprintEngine(registry=_add_registry)
        exec_result = engine.run(bp, inputs=bp.inputs)
        assert exec_result.outputs["sum"] == pytest.approx(15.0)
