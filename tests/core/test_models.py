"""Tests for bricks.core.models."""

from __future__ import annotations

import pytest

from bricks.core.models import BlueprintDefinition, BrickMeta, StepDefinition


class TestBrickMeta:
    def test_defaults(self) -> None:
        meta = BrickMeta(name="test")
        assert meta.tags == [], f"Expected [], got {meta.tags!r}"
        assert meta.destructive is False, f"Expected False, got {meta.destructive!r}"
        assert meta.idempotent is True, f"Expected True, got {meta.idempotent!r}"

    def test_name_required(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            BrickMeta()  # type: ignore[call-arg]


class TestStepDefinition:
    def test_minimal_step(self) -> None:
        step = StepDefinition(name="step1", brick="my_brick")
        assert step.params == {}, f"Expected {{}}, got {step.params!r}"
        assert step.save_as is None, f"Expected None, got {step.save_as!r}"

    def test_save_as_can_be_set(self) -> None:
        step = StepDefinition(name="s1", brick="b", save_as="result")
        assert step.save_as == "result", f"Expected 'result', got {step.save_as!r}"

    def test_params_can_be_set(self) -> None:
        step = StepDefinition(name="s1", brick="b", params={"x": 42})
        assert step.params == {"x": 42}, f"Expected {{'x': 42}}, got {step.params!r}"

    def test_brick_name_stored(self) -> None:
        step = StepDefinition(name="s1", brick="my_op")
        assert step.brick == "my_op", f"Expected 'my_op', got {step.brick!r}"

    def test_step_name_stored(self) -> None:
        step = StepDefinition(name="my_step", brick="b")
        assert step.name == "my_step", f"Expected 'my_step', got {step.name!r}"


class TestBlueprintDefinition:
    def test_minimal_blueprint(self) -> None:
        bp = BlueprintDefinition(name="test_bp")
        assert bp.steps == [], f"Expected [], got {bp.steps!r}"
        assert bp.outputs_map == {}, f"Expected {{}}, got {bp.outputs_map!r}"

    def test_inputs_default_empty(self) -> None:
        bp = BlueprintDefinition(name="test")
        assert bp.inputs == {}, f"Expected {{}}, got {bp.inputs!r}"

    def test_steps_can_be_added(self) -> None:
        step = StepDefinition(name="s1", brick="b")
        bp = BlueprintDefinition(name="test", steps=[step])
        assert len(bp.steps) == 1, f"Expected length 1, got {len(bp.steps)}"
        assert bp.steps[0].name == "s1", f"Expected 's1', got {bp.steps[0].name!r}"

    def test_outputs_map_can_be_set(self) -> None:
        bp = BlueprintDefinition(name="test", outputs_map={"result": "${val}"})
        assert bp.outputs_map == {"result": "${val}"}, "Expected outputs_map mismatch"

    def test_description_default_empty(self) -> None:
        bp = BlueprintDefinition(name="test")
        assert bp.description == "", f"Expected '', got {bp.description!r}"

    def test_description_can_be_set(self) -> None:
        bp = BlueprintDefinition(name="test", description="My blueprint")
        assert bp.description == "My blueprint", f"Expected 'My blueprint', got {bp.description!r}"

    def test_name_required(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            BlueprintDefinition()  # type: ignore[call-arg]


class TestBrickMetaDefaults:
    def test_tags_default_empty(self) -> None:
        meta = BrickMeta(name="my_brick")
        assert meta.tags == [], f"Expected [], got {meta.tags!r}"

    def test_destructive_default_false(self) -> None:
        meta = BrickMeta(name="my_brick")
        assert meta.destructive is False, f"Expected False, got {meta.destructive!r}"

    def test_idempotent_default_true(self) -> None:
        meta = BrickMeta(name="my_brick")
        assert meta.idempotent is True, f"Expected True, got {meta.idempotent!r}"

    def test_description_default_empty(self) -> None:
        meta = BrickMeta(name="my_brick")
        assert meta.description == "", f"Expected '', got {meta.description!r}"

    def test_tags_can_be_set(self) -> None:
        meta = BrickMeta(name="my_brick", tags=["math", "io"])
        assert meta.tags == ["math", "io"], f"Expected ['math', 'io'], got {meta.tags!r}"

    def test_destructive_can_be_true(self) -> None:
        meta = BrickMeta(name="my_brick", destructive=True)
        assert meta.destructive is True, f"Expected True, got {meta.destructive!r}"

    def test_idempotent_can_be_false(self) -> None:
        meta = BrickMeta(name="my_brick", idempotent=False)
        assert meta.idempotent is False, f"Expected False, got {meta.idempotent!r}"
