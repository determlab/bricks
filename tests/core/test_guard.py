"""Tests for guard step type in BlueprintEngine."""

from __future__ import annotations

import pytest

from bricks.core.engine import BlueprintEngine
from bricks.core.exceptions import GuardFailedError
from bricks.core.models import BlueprintDefinition, StepDefinition
from bricks.core.registry import BrickRegistry


def _registry_with_echo() -> BrickRegistry:
    """Return a registry with a simple echo brick."""
    from bricks.core.brick import brick

    registry = BrickRegistry()

    @brick(tags=[], destructive=False)
    def echo(value: int) -> dict[str, int]:
        """Return the value unchanged."""
        return {"result": value}

    registry.register("echo", echo, echo.__brick_meta__)
    return registry


def test_guard_passes_when_condition_true() -> None:
    registry = _registry_with_echo()
    engine = BlueprintEngine(registry)

    blueprint = BlueprintDefinition(
        name="test",
        steps=[
            StepDefinition(name="step1", brick="echo", params={"value": 5}, save_as="s1"),
            StepDefinition(
                name="check",
                type="guard",
                condition="s1['result'] > 0",
                message="Expected positive result",
            ),
        ],
    )
    result = engine.run(blueprint)
    assert result.outputs == {}


def test_guard_fails_when_condition_false() -> None:
    registry = _registry_with_echo()
    engine = BlueprintEngine(registry)

    blueprint = BlueprintDefinition(
        name="test",
        steps=[
            StepDefinition(name="step1", brick="echo", params={"value": -1}, save_as="s1"),
            StepDefinition(
                name="check",
                type="guard",
                condition="s1['result'] > 0",
                message="Expected positive result",
            ),
        ],
    )
    with pytest.raises(GuardFailedError) as exc_info:
        engine.run(blueprint)
    assert "check" in str(exc_info.value)
    assert "Expected positive result" in str(exc_info.value)


def test_guard_error_message_includes_condition() -> None:
    registry = _registry_with_echo()
    engine = BlueprintEngine(registry)

    blueprint = BlueprintDefinition(
        name="test",
        steps=[
            StepDefinition(name="s", brick="echo", params={"value": 0}, save_as="s"),
            StepDefinition(
                name="g",
                type="guard",
                condition="s['result'] == 99",
                message="must be 99",
            ),
        ],
    )
    with pytest.raises(GuardFailedError) as exc_info:
        engine.run(blueprint)
    err = str(exc_info.value)
    assert "s['result'] == 99" in err


def test_guard_raises_on_bad_expression() -> None:
    registry = _registry_with_echo()
    engine = BlueprintEngine(registry)

    blueprint = BlueprintDefinition(
        name="test",
        steps=[
            StepDefinition(
                name="bad_guard",
                type="guard",
                condition="undefined_var > 0",
                message="should error",
            ),
        ],
    )
    with pytest.raises(GuardFailedError) as exc_info:
        engine.run(blueprint)
    assert "Condition raised an error" in str(exc_info.value)


def test_guard_without_condition_raises_validation_error() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        StepDefinition(name="g", type="guard")


def test_guard_default_message_used_when_none_provided() -> None:
    registry = _registry_with_echo()
    engine = BlueprintEngine(registry)

    blueprint = BlueprintDefinition(
        name="test",
        steps=[
            StepDefinition(
                name="g",
                type="guard",
                condition="False",
            ),
        ],
    )
    with pytest.raises(GuardFailedError) as exc_info:
        engine.run(blueprint)
    assert "Guard condition not met" in str(exc_info.value)
