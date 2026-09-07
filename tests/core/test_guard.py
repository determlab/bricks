"""Tests for the guard step type in BlueprintEngine.

A guard names a predicate brick (D13, RFC-002). The engine looks the brick up
in the registry, calls it with the step's resolved params, and takes the
truthiness of its result. No string from a blueprint is executed as code.
"""

from __future__ import annotations

from typing import Any

import pytest

from bricks.core.brick import brick
from bricks.core.engine import BlueprintEngine
from bricks.core.exceptions import (
    BlueprintValidationError,
    BrickExecutionError,
    BrickNotFoundError,
    GuardFailedError,
)
from bricks.core.models import BlueprintDefinition, BrickMeta, StepDefinition
from bricks.core.registry import BrickRegistry
from bricks.core.validation import BlueprintValidator

# The escape payload RFC-002 names: the standard `__builtins__`-emptied `eval`
# bypass. It must never be treated as anything but an (absent) brick name.
ESCAPE_PAYLOAD = "().__class__.__base__.__subclasses__()"


def _registry() -> BrickRegistry:
    """Return a registry with an echo brick and two predicate bricks."""
    registry = BrickRegistry()

    @brick(tags=[], destructive=False)
    def echo(value: int) -> dict[str, int]:
        """Return the value unchanged."""
        return {"result": value}

    @brick(tags=[], destructive=False)
    def is_positive(value: int) -> dict[str, bool]:
        """Return whether the value is greater than zero."""
        return {"result": value > 0}

    @brick(tags=[], destructive=False)
    def raw_bool(value: int) -> bool:
        """Return a bare bool rather than the usual result dict."""
        return value > 0

    registry.register("echo", echo, echo.__brick_meta__)
    registry.register("is_positive", is_positive, is_positive.__brick_meta__)
    registry.register("raw_bool", raw_bool, raw_bool.__brick_meta__)
    return registry


def _guarded_blueprint(guard_brick: str, value: int) -> BlueprintDefinition:
    """A blueprint of [echo -> guard on the echoed value]."""
    return BlueprintDefinition(
        name="test",
        steps=[
            StepDefinition(name="step1", brick="echo", params={"value": value}, save_as="s1"),
            StepDefinition(
                name="check",
                type="guard",
                brick=guard_brick,
                params={"value": "${s1.result}"},
                message="Expected positive result",
            ),
        ],
    )


# ── Passing and failing predicates ─────────────────────────────────────────────


def test_guard_passes_when_predicate_truthy() -> None:
    engine = BlueprintEngine(_registry())
    result = engine.run(_guarded_blueprint("is_positive", 5))
    assert result.outputs == {}


def test_guard_fails_when_predicate_falsy() -> None:
    engine = BlueprintEngine(_registry())
    with pytest.raises(GuardFailedError) as exc_info:
        engine.run(_guarded_blueprint("is_positive", -1))
    assert "check" in str(exc_info.value)
    assert "Expected positive result" in str(exc_info.value)


def test_guard_error_names_the_step_and_the_brick() -> None:
    """D8: a failure names the step and the brick that caused it."""
    engine = BlueprintEngine(_registry())
    with pytest.raises(GuardFailedError) as exc_info:
        engine.run(_guarded_blueprint("is_positive", 0))
    err = exc_info.value
    assert err.step_name == "check"
    assert err.brick_name == "is_positive"
    assert "'check'" in str(err)
    assert "'is_positive'" in str(err)


def test_guard_accepts_a_bare_bool_return() -> None:
    """Return handling matches __branch__: dict -> result key, else truthiness."""
    engine = BlueprintEngine(_registry())
    assert engine.run(_guarded_blueprint("raw_bool", 3)).outputs == {}
    with pytest.raises(GuardFailedError):
        engine.run(_guarded_blueprint("raw_bool", -3))


def test_guard_default_message_used_when_none_provided() -> None:
    registry = _registry()
    engine = BlueprintEngine(registry)
    blueprint = BlueprintDefinition(
        name="test",
        steps=[StepDefinition(name="g", type="guard", brick="is_positive", params={"value": -1})],
    )
    with pytest.raises(GuardFailedError) as exc_info:
        engine.run(blueprint)
    assert "Guard condition not met" in str(exc_info.value)


# ── A predicate that raises is a brick failure, not a guard rejection ──────────


def test_guard_predicate_that_raises_is_a_brick_execution_error() -> None:
    registry = _registry()

    @brick(tags=[], destructive=False)
    def boom(value: int) -> dict[str, bool]:
        """Always raise."""
        raise RuntimeError("predicate exploded")

    registry.register("boom", boom, boom.__brick_meta__)
    engine = BlueprintEngine(registry)

    with pytest.raises(BrickExecutionError) as exc_info:
        engine.run(_guarded_blueprint("boom", 1))
    err = exc_info.value
    assert err.brick_name == "boom"
    assert err.step_name == "check"
    assert isinstance(err.cause, RuntimeError)


def test_guard_inner_brick_execution_error_propagates_unchanged() -> None:
    """An already-attributed inner failure keeps the real brick's name (#34)."""
    registry = _registry()
    inner = BrickExecutionError(brick_name="inner_brick", step_name="inner_step", cause=ValueError("nope"))

    def relay(**kwargs: Any) -> dict[str, bool]:
        raise inner

    registry.register("relay", relay, BrickMeta(name="relay", description="re-raises an attributed error"))
    engine = BlueprintEngine(registry)

    with pytest.raises(BrickExecutionError) as exc_info:
        engine.run(_guarded_blueprint("relay", 1))
    assert exc_info.value is inner


# ── Model-level field constraints ─────────────────────────────────────────────


def test_guard_without_brick_raises_validation_error() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="Guard step must specify 'brick'"):
        StepDefinition(name="g", type="guard")


def test_guard_with_blueprint_is_rejected() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="Guard step cannot specify 'blueprint'"):
        StepDefinition(name="g", type="guard", brick="is_positive", blueprint="child.yaml")


def test_old_condition_form_fails_loudly() -> None:
    """A pre-D13 guard carrying `condition:` no longer builds a step at all."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="Guard step must specify 'brick'"):
        StepDefinition(name="g", type="guard", condition="s1['result'] > 0")


# ── Unknown brick names, including the RFC's escape payload ───────────────────


def test_unknown_guard_brick_fails_validation_before_execution() -> None:
    registry = _registry()
    blueprint = _guarded_blueprint("no_such_brick", 5)

    with pytest.raises(BlueprintValidationError) as exc_info:
        BlueprintValidator(registry=registry).validate(blueprint)
    assert any("no_such_brick" in e for e in exc_info.value.errors)


def test_escape_payload_is_rejected_by_the_validator() -> None:
    """Route 1: the payload reaches BlueprintValidator and is an unknown brick."""
    registry = _registry()
    blueprint = _guarded_blueprint(ESCAPE_PAYLOAD, 5)

    with pytest.raises(BlueprintValidationError) as exc_info:
        BlueprintValidator(registry=registry).validate(blueprint)
    assert any(ESCAPE_PAYLOAD in e for e in exc_info.value.errors)


def test_escape_payload_is_rejected_by_the_engine_without_validation() -> None:
    """Route 2: `bricks run` skips validation (G8), so it must die at lookup.

    The payload is only ever a name handed to ``registry.get`` — it is never
    parsed, compiled or evaluated, so the only outcome is BrickNotFoundError.
    """
    registry = _registry()
    engine = BlueprintEngine(registry)

    with pytest.raises(BrickNotFoundError) as exc_info:
        engine.run(_guarded_blueprint(ESCAPE_PAYLOAD, 5))
    assert exc_info.value.name == ESCAPE_PAYLOAD


# ── Teardown (engine.py class docstring: failing step, then reverse order) ─────


def _registry_with_teardown(calls: list[str]) -> BrickRegistry:
    """Registry whose ``setup`` brick records a teardown call."""
    registry = _registry()

    def _on_teardown(inputs: dict[str, Any], error: Exception) -> None:
        calls.append("setup")

    @brick(tags=[], destructive=False, teardown=_on_teardown)
    def setup(value: int) -> dict[str, int]:
        """Acquire a notional resource."""
        return {"result": value}

    registry.register("setup", setup, setup.__brick_meta__)
    return registry


def test_teardown_runs_on_completed_steps_when_a_guard_fails() -> None:
    """[brick-with-teardown, guard]: a guard stopping the run still tears down."""
    calls: list[str] = []
    engine = BlueprintEngine(_registry_with_teardown(calls))
    blueprint = BlueprintDefinition(
        name="test",
        steps=[
            StepDefinition(name="acquire", brick="setup", params={"value": -1}, save_as="s1"),
            StepDefinition(
                name="check",
                type="guard",
                brick="is_positive",
                params={"value": "${s1.result}"},
                message="must be positive",
            ),
        ],
    )
    with pytest.raises(GuardFailedError):
        engine.run(blueprint)
    assert calls == ["setup"]


def test_teardown_runs_on_completed_steps_when_a_guard_predicate_raises() -> None:
    calls: list[str] = []
    registry = _registry_with_teardown(calls)

    @brick(tags=[], destructive=False)
    def boom(value: int) -> dict[str, bool]:
        """Always raise."""
        raise RuntimeError("predicate exploded")

    registry.register("boom", boom, boom.__brick_meta__)
    engine = BlueprintEngine(registry)

    blueprint = BlueprintDefinition(
        name="test",
        steps=[
            StepDefinition(name="acquire", brick="setup", params={"value": 1}, save_as="s1"),
            StepDefinition(name="check", type="guard", brick="boom", params={"value": "${s1.result}"}),
        ],
    )
    with pytest.raises(BrickExecutionError):
        engine.run(blueprint)
    assert calls == ["setup"]


def test_teardown_not_run_when_the_guard_passes() -> None:
    calls: list[str] = []
    engine = BlueprintEngine(_registry_with_teardown(calls))
    blueprint = BlueprintDefinition(
        name="test",
        steps=[
            StepDefinition(name="acquire", brick="setup", params={"value": 1}, save_as="s1"),
            StepDefinition(name="check", type="guard", brick="is_positive", params={"value": "${s1.result}"}),
        ],
    )
    engine.run(blueprint)
    assert calls == []
