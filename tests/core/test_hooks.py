"""Tests for the pluggy hook spec in :mod:`bricks.core.hooks`.

Registers a recording plugin, runs a minimal blueprint through the
engine, and asserts the expected lifecycle events fire in the expected
order with the right payload shapes.
"""

from __future__ import annotations

from typing import Any

from bricks.core.builtins import register_builtins
from bricks.core.engine import BlueprintEngine
from bricks.core.hooks import get_plugin_manager, hookimpl
from bricks.core.models import BlueprintDefinition, BrickMeta, StepDefinition
from bricks.core.registry import BrickRegistry


class _RecordingPlugin:
    """Plugin that records every hook call as ``(phase, payload)`` tuples."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    @hookimpl
    def compose_start(self, task: str) -> None:
        self.events.append(("compose_start", {"task": task}))

    @hookimpl
    def compose_done(self, dsl: str, tokens_in: int, tokens_out: int) -> None:
        self.events.append(("compose_done", {"dsl": dsl, "tokens_in": tokens_in, "tokens_out": tokens_out}))

    @hookimpl
    def execute_start(self, blueprint_yaml: str) -> None:
        self.events.append(("execute_start", {"blueprint_yaml": blueprint_yaml}))

    @hookimpl
    def step_start(self, step_name: str, brick_name: str) -> None:
        self.events.append(("step_start", {"step_name": step_name, "brick_name": brick_name}))

    @hookimpl
    def step_done(self, step_name: str, brick_name: str, duration_ms: int) -> None:
        self.events.append(
            ("step_done", {"step_name": step_name, "brick_name": brick_name, "duration_ms": duration_ms})
        )

    @hookimpl
    def heal_attempt(self, tier: int, healer_name: str, succeeded: bool) -> None:
        self.events.append(("heal_attempt", {"tier": tier, "healer_name": healer_name, "succeeded": succeeded}))

    @hookimpl
    def raw_llm_start(self) -> None:
        self.events.append(("raw_llm_start", {}))

    @hookimpl
    def raw_llm_done(self, response: str, tokens_in: int, tokens_out: int) -> None:
        self.events.append(("raw_llm_done", {"response": response, "tokens_in": tokens_in, "tokens_out": tokens_out}))

    @hookimpl
    def check_done(self, key: str, expected: Any, got: Any, passed: bool) -> None:
        self.events.append(("check_done", {"key": key, "expected": expected, "got": got, "passed": passed}))

    @hookimpl
    def run_failed(self, error: str) -> None:
        self.events.append(("run_failed", {"error": error}))


def test_engine_fires_step_start_and_step_done_in_order() -> None:
    """BlueprintEngine with a plugin_manager emits step_start → step_done
    for each top-level brick step, in the order the steps run."""
    reg = BrickRegistry()
    register_builtins(reg)

    def add(a: int, b: int) -> dict[str, int]:
        return {"result": a + b}

    def double(x: int) -> dict[str, int]:
        return {"result": x * 2}

    reg.register("add", add, BrickMeta(name="add", description="sum"))
    reg.register("double", double, BrickMeta(name="double", description="x2"))

    pm = get_plugin_manager()
    recorder = _RecordingPlugin()
    pm.register(recorder)

    engine = BlueprintEngine(registry=reg, plugin_manager=pm)
    bp = BlueprintDefinition(
        name="test",
        steps=[
            StepDefinition(name="s1", brick="add", params={"a": 3, "b": 4}, save_as="sum"),
            StepDefinition(name="s2", brick="double", params={"x": "${sum.result}"}),
        ],
    )
    engine.run(bp)

    phases = [e[0] for e in recorder.events]
    assert phases == ["step_start", "step_done", "step_start", "step_done"], phases
    # Names arrive in order.
    assert recorder.events[0][1]["brick_name"] == "add"
    assert recorder.events[1][1]["step_name"] == "s1"
    assert recorder.events[2][1]["brick_name"] == "double"
    # duration_ms is an int, non-negative.
    assert isinstance(recorder.events[1][1]["duration_ms"], int)
    assert recorder.events[1][1]["duration_ms"] >= 0


def test_engine_without_plugin_manager_is_silent() -> None:
    """A default ``BlueprintEngine(registry=...)`` does not require pluggy
    and must not raise when no PluginManager is provided."""
    reg = BrickRegistry()

    def nop(x: int) -> dict[str, int]:
        return {"result": x}

    reg.register("nop", nop, BrickMeta(name="nop", description="nop"))
    engine = BlueprintEngine(registry=reg)  # no plugin_manager kwarg
    out = engine.run(
        BlueprintDefinition(
            name="silent",
            steps=[StepDefinition(name="s1", brick="nop", params={"x": 1})],
        )
    )
    assert out is not None


def test_plugin_with_missing_hook_methods_is_ok() -> None:
    """Pluggy must tolerate a plugin that implements only a subset of
    hooks. Only the implemented ones fire; the rest are silently skipped."""

    class PartialPlugin:
        def __init__(self) -> None:
            self.only_starts: list[str] = []

        @hookimpl
        def step_start(self, step_name: str, brick_name: str) -> None:
            self.only_starts.append(step_name)

    reg = BrickRegistry()

    def nop(x: int) -> dict[str, int]:
        return {"result": x}

    reg.register("nop", nop, BrickMeta(name="nop", description="nop"))

    pm = get_plugin_manager()
    plugin = PartialPlugin()
    pm.register(plugin)

    engine = BlueprintEngine(registry=reg, plugin_manager=pm)
    engine.run(
        BlueprintDefinition(
            name="partial",
            steps=[StepDefinition(name="only_one", brick="nop", params={"x": 1})],
        )
    )
    assert plugin.only_starts == ["only_one"]
