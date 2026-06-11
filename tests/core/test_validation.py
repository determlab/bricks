"""Tests for bricks.core.validation."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from bricks.core.exceptions import BlueprintValidationError
from bricks.core.models import BlueprintDefinition, StepDefinition
from bricks.core.registry import BrickRegistry
from bricks.core.validation import BlueprintValidator


class TestCheck1MissingBrick:
    def test_missing_brick_fails_validation(self) -> None:
        reg = BrickRegistry()
        validator = BlueprintValidator(registry=reg)
        bp = BlueprintDefinition(
            name="test",
            steps=[StepDefinition(name="s1", brick="nonexistent")],
        )
        with pytest.raises(BlueprintValidationError):
            validator.validate(bp)

    def test_present_brick_passes(self, stub_registry_factory: Callable[..., BrickRegistry]) -> None:
        reg = stub_registry_factory("my_brick")
        validator = BlueprintValidator(registry=reg)
        bp = BlueprintDefinition(
            name="test",
            steps=[StepDefinition(name="s1", brick="my_brick")],
        )
        validator.validate(bp)  # raises BlueprintValidationError on failure


class TestCheck2SaveAsUniqueness:
    def test_duplicate_save_as_fails(self, stub_registry_factory: Callable[..., BrickRegistry]) -> None:
        reg = stub_registry_factory("brick_a", "brick_b")
        validator = BlueprintValidator(registry=reg)
        bp = BlueprintDefinition(
            name="test",
            steps=[
                StepDefinition(name="s1", brick="brick_a", save_as="result"),
                StepDefinition(name="s2", brick="brick_b", save_as="result"),
            ],
        )
        with pytest.raises(BlueprintValidationError) as exc_info:
            validator.validate(bp)
        assert any("result" in e for e in exc_info.value.errors), (
            f"Expected 'result' in errors: {exc_info.value.errors!r}"
        )

    def test_unique_save_as_passes(self, stub_registry_factory: Callable[..., BrickRegistry]) -> None:
        reg = stub_registry_factory("brick_a", "brick_b")
        validator = BlueprintValidator(registry=reg)
        bp = BlueprintDefinition(
            name="test",
            steps=[
                StepDefinition(name="s1", brick="brick_a", save_as="result1"),
                StepDefinition(name="s2", brick="brick_b", save_as="result2"),
            ],
        )
        validator.validate(bp)  # raises BlueprintValidationError on failure


class TestCheck3DuplicateStepNames:
    def test_duplicate_step_name_fails(self, stub_registry_factory: Callable[..., BrickRegistry]) -> None:
        reg = stub_registry_factory("brick_a")
        validator = BlueprintValidator(registry=reg)
        bp = BlueprintDefinition(
            name="test",
            steps=[
                StepDefinition(name="s1", brick="brick_a"),
                StepDefinition(name="s1", brick="brick_a"),
            ],
        )
        with pytest.raises(BlueprintValidationError) as exc_info:
            validator.validate(bp)
        assert any("Duplicate step name" in e for e in exc_info.value.errors), (
            f"Expected 'Duplicate step name' in errors: {exc_info.value.errors!r}"
        )

    def test_unique_step_names_pass(self, stub_registry_factory: Callable[..., BrickRegistry]) -> None:
        reg = stub_registry_factory("brick_a")
        validator = BlueprintValidator(registry=reg)
        bp = BlueprintDefinition(
            name="test",
            steps=[
                StepDefinition(name="s1", brick="brick_a"),
                StepDefinition(name="s2", brick="brick_a"),
            ],
        )
        validator.validate(bp)  # raises BlueprintValidationError on failure


class TestCheck4OutputsMapReferences:
    def test_outputs_map_undefined_reference_fails(self, stub_registry_factory: Callable[..., BrickRegistry]) -> None:
        reg = stub_registry_factory("brick_a")
        validator = BlueprintValidator(registry=reg)
        bp = BlueprintDefinition(
            name="test",
            steps=[StepDefinition(name="s1", brick="brick_a", save_as="val")],
            outputs_map={"out": "${nonexistent}"},
        )
        with pytest.raises(BlueprintValidationError):
            validator.validate(bp)

    def test_outputs_map_valid_save_as_passes(self, stub_registry_factory: Callable[..., BrickRegistry]) -> None:
        reg = stub_registry_factory("brick_a")
        validator = BlueprintValidator(registry=reg)
        bp = BlueprintDefinition(
            name="test",
            steps=[StepDefinition(name="s1", brick="brick_a", save_as="val")],
            outputs_map={"out": "${val}"},
        )
        validator.validate(bp)  # raises BlueprintValidationError on failure

    def test_outputs_map_valid_input_ref_passes(self, stub_registry_factory: Callable[..., BrickRegistry]) -> None:
        reg = stub_registry_factory("brick_a")
        validator = BlueprintValidator(registry=reg)
        bp = BlueprintDefinition(
            name="test",
            inputs={"x": "int"},
            steps=[StepDefinition(name="s1", brick="brick_a")],
            outputs_map={"out": "${inputs.x}"},
        )
        validator.validate(bp)  # raises BlueprintValidationError on failure


class TestCheck5InputReferences:
    def test_undeclared_input_ref_fails(self, stub_registry_factory: Callable[..., BrickRegistry]) -> None:
        reg = stub_registry_factory("brick_a")
        validator = BlueprintValidator(registry=reg)
        bp = BlueprintDefinition(
            name="test",
            inputs={"x": "int"},
            steps=[
                StepDefinition(
                    name="s1",
                    brick="brick_a",
                    params={"val": "${inputs.y}"},
                )
            ],
        )
        with pytest.raises(BlueprintValidationError) as exc_info:
            validator.validate(bp)
        assert any("y" in e for e in exc_info.value.errors), f"Expected 'y' in errors: {exc_info.value.errors!r}"

    def test_declared_input_ref_passes(self, stub_registry_factory: Callable[..., BrickRegistry]) -> None:
        reg = stub_registry_factory("brick_a")
        validator = BlueprintValidator(registry=reg)
        bp = BlueprintDefinition(
            name="test",
            inputs={"x": "int"},
            steps=[
                StepDefinition(
                    name="s1",
                    brick="brick_a",
                    params={"val": "${inputs.x}"},
                )
            ],
        )
        validator.validate(bp)  # raises BlueprintValidationError on failure

    @pytest.mark.parametrize(
        "params,label",
        [
            ({"nested": {"key": "${inputs.missing}"}}, "dict"),
            ({"items": ["${inputs.missing}"]}, "list"),
        ],
    )
    def test_nested_params_checked(
        self,
        params: dict[str, object],
        label: str,
        stub_registry_factory: Callable[..., BrickRegistry],
    ) -> None:
        """References inside nested dict and list params are validated."""
        reg = stub_registry_factory("brick_a")
        validator = BlueprintValidator(registry=reg)
        bp = BlueprintDefinition(
            name="test",
            inputs={},
            steps=[StepDefinition(name="s1", brick="brick_a", params=params)],
        )
        with pytest.raises(BlueprintValidationError):
            validator.validate(bp)


class TestCheck6ResultReferences:
    def test_forward_reference_fails(self, stub_registry_factory: Callable[..., BrickRegistry]) -> None:
        reg = stub_registry_factory("brick_a", "brick_b")
        validator = BlueprintValidator(registry=reg)
        bp = BlueprintDefinition(
            name="test",
            steps=[
                StepDefinition(
                    name="s1",
                    brick="brick_a",
                    params={"val": "${future_result}"},
                ),
                StepDefinition(
                    name="s2",
                    brick="brick_b",
                    save_as="future_result",
                ),
            ],
        )
        with pytest.raises(BlueprintValidationError) as exc_info:
            validator.validate(bp)
        assert any("not yet available" in e for e in exc_info.value.errors), (
            f"Expected 'not yet available' in errors: {exc_info.value.errors!r}"
        )

    def test_undefined_variable_fails(self, stub_registry_factory: Callable[..., BrickRegistry]) -> None:
        reg = stub_registry_factory("brick_a")
        validator = BlueprintValidator(registry=reg)
        bp = BlueprintDefinition(
            name="test",
            steps=[
                StepDefinition(
                    name="s1",
                    brick="brick_a",
                    params={"val": "${totally_undefined}"},
                )
            ],
        )
        with pytest.raises(BlueprintValidationError) as exc_info:
            validator.validate(bp)
        assert any("undefined variable" in e for e in exc_info.value.errors), (
            f"Expected 'undefined variable' in errors: {exc_info.value.errors!r}"
        )

    def test_valid_backward_reference_passes(self, stub_registry_factory: Callable[..., BrickRegistry]) -> None:
        reg = stub_registry_factory("brick_a", "brick_b")
        validator = BlueprintValidator(registry=reg)
        bp = BlueprintDefinition(
            name="test",
            steps=[
                StepDefinition(name="s1", brick="brick_a", save_as="first"),
                StepDefinition(
                    name="s2",
                    brick="brick_b",
                    params={"val": "${first}"},
                ),
            ],
        )
        validator.validate(bp)  # raises BlueprintValidationError on failure

    def test_multiple_errors_collected(self, stub_registry_factory: Callable[..., BrickRegistry]) -> None:
        reg = stub_registry_factory("brick_a")
        validator = BlueprintValidator(registry=reg)
        bp = BlueprintDefinition(
            name="test",
            steps=[
                StepDefinition(
                    name="s1",
                    brick="brick_a",
                    params={"a": "${inputs.missing}", "b": "${undefined}"},
                )
            ],
        )
        with pytest.raises(BlueprintValidationError) as exc_info:
            validator.validate(bp)
        err = exc_info.value
        assert len(err.errors) >= 2, f"Expected at least 2 errors, got {len(err.errors)}"


class TestCheck7EmptyBlueprint:
    def test_empty_blueprint_fails(self) -> None:
        reg = BrickRegistry()
        validator = BlueprintValidator(registry=reg)
        bp = BlueprintDefinition(name="empty")
        with pytest.raises(BlueprintValidationError) as exc_info:
            validator.validate(bp)
        assert any("no steps" in e for e in exc_info.value.errors), (
            f"Expected 'no steps' in errors: {exc_info.value.errors!r}"
        )
