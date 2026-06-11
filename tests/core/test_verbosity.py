"""Tests for BlueprintEngine verbosity levels and ExecutionResult structure."""

from __future__ import annotations

from typing import cast

from bricks.core.brick import BrickFunction, brick
from bricks.core.engine import BlueprintEngine
from bricks.core.models import BlueprintDefinition, ExecutionResult, StepDefinition, Verbosity
from bricks.core.registry import BrickRegistry


def _make_registry() -> BrickRegistry:
    """Registry with two simple math bricks."""
    reg = BrickRegistry()

    @brick(description="Add two numbers")
    def add(a: float, b: float) -> dict[str, float]:
        """Return a + b."""
        return {"result": a + b}

    @brick(description="Multiply two numbers")
    def multiply(a: float, b: float) -> dict[str, float]:
        """Return a * b."""
        return {"result": a * b}

    for fn in (add, multiply):
        bf = cast(BrickFunction, fn)
        reg.register(bf.__brick_meta__.name, bf, bf.__brick_meta__)
    return reg


def _two_step_blueprint() -> BlueprintDefinition:
    return BlueprintDefinition(
        name="two_step",
        steps=[
            StepDefinition(name="step_add", brick="add", params={"a": 3.0, "b": 4.0}, save_as="s1"),
            StepDefinition(name="step_mul", brick="multiply", params={"a": "${s1.result}", "b": 2.0}, save_as="s2"),
        ],
        outputs_map={"result": "${s2.result}"},
    )


class TestMinimalVerbosity:
    def test_outputs_correct(self) -> None:
        engine = BlueprintEngine(registry=_make_registry())
        result = engine.run(_two_step_blueprint())
        assert result.outputs["result"] == 14.0

    def test_steps_empty(self) -> None:
        engine = BlueprintEngine(registry=_make_registry())
        result = engine.run(_two_step_blueprint())
        assert result.steps == []

    def test_total_duration_zero(self) -> None:
        engine = BlueprintEngine(registry=_make_registry())
        result = engine.run(_two_step_blueprint())
        assert result.total_duration_ms == 0.0

    def test_verbosity_field(self) -> None:
        engine = BlueprintEngine(registry=_make_registry())
        result = engine.run(_two_step_blueprint())
        assert result.verbosity == Verbosity.MINIMAL

    def test_blueprint_name(self) -> None:
        engine = BlueprintEngine(registry=_make_registry())
        result = engine.run(_two_step_blueprint())
        assert result.blueprint_name == "two_step"

    def test_outputs_match_old_dict_return(self) -> None:
        """outputs dict matches what the old run() returned."""
        engine = BlueprintEngine(registry=_make_registry())
        result = engine.run(_two_step_blueprint())
        assert isinstance(result, ExecutionResult)
        assert result.outputs == {"result": 14.0}


class TestStandardVerbosity:
    def test_steps_count(self) -> None:
        engine = BlueprintEngine(registry=_make_registry())
        result = engine.run(_two_step_blueprint(), verbosity=Verbosity.STANDARD)
        assert len(result.steps) == 2

    def test_step_names_and_brick_names(self) -> None:
        engine = BlueprintEngine(registry=_make_registry())
        result = engine.run(_two_step_blueprint(), verbosity=Verbosity.STANDARD)
        assert result.steps[0].step_name == "step_add"
        assert result.steps[0].brick_name == "add"
        assert result.steps[1].step_name == "step_mul"
        assert result.steps[1].brick_name == "multiply"

    def test_step_outputs_populated(self) -> None:
        engine = BlueprintEngine(registry=_make_registry())
        result = engine.run(_two_step_blueprint(), verbosity=Verbosity.STANDARD)
        assert result.steps[0].outputs == {"result": 7.0}
        assert result.steps[1].outputs == {"result": 14.0}

    def test_step_inputs_empty(self) -> None:
        """STANDARD verbosity does not populate step inputs."""
        engine = BlueprintEngine(registry=_make_registry())
        result = engine.run(_two_step_blueprint(), verbosity=Verbosity.STANDARD)
        assert result.steps[0].inputs == {}
        assert result.steps[1].inputs == {}

    def test_total_duration_zero(self) -> None:
        engine = BlueprintEngine(registry=_make_registry())
        result = engine.run(_two_step_blueprint(), verbosity=Verbosity.STANDARD)
        assert result.total_duration_ms == 0.0

    def test_outputs_correct(self) -> None:
        engine = BlueprintEngine(registry=_make_registry())
        result = engine.run(_two_step_blueprint(), verbosity=Verbosity.STANDARD)
        assert result.outputs == {"result": 14.0}

    def test_verbosity_field(self) -> None:
        engine = BlueprintEngine(registry=_make_registry())
        result = engine.run(_two_step_blueprint(), verbosity=Verbosity.STANDARD)
        assert result.verbosity == Verbosity.STANDARD


class TestFullVerbosity:
    def test_step_inputs_populated(self) -> None:
        engine = BlueprintEngine(registry=_make_registry())
        result = engine.run(_two_step_blueprint(), verbosity=Verbosity.FULL)
        assert result.steps[0].inputs == {"a": 3.0, "b": 4.0}

    def test_step_duration_positive(self) -> None:
        engine = BlueprintEngine(registry=_make_registry())
        result = engine.run(_two_step_blueprint(), verbosity=Verbosity.FULL)
        for step in result.steps:
            assert step.duration_ms > 0.0

    def test_total_duration_positive(self) -> None:
        engine = BlueprintEngine(registry=_make_registry())
        result = engine.run(_two_step_blueprint(), verbosity=Verbosity.FULL)
        assert result.total_duration_ms > 0.0

    def test_outputs_correct(self) -> None:
        engine = BlueprintEngine(registry=_make_registry())
        result = engine.run(_two_step_blueprint(), verbosity=Verbosity.FULL)
        assert result.outputs == {"result": 14.0}

    def test_verbosity_field(self) -> None:
        engine = BlueprintEngine(registry=_make_registry())
        result = engine.run(_two_step_blueprint(), verbosity=Verbosity.FULL)
        assert result.verbosity == Verbosity.FULL
