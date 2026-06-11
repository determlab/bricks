"""Tests for teardown hooks on BaseBrick, @brick decorator, and BlueprintEngine."""

from __future__ import annotations

from typing import Any, ClassVar, cast

import pytest

from bricks.core.brick import BaseBrick, BrickFunction, BrickModel, brick
from bricks.core.engine import BlueprintEngine
from bricks.core.exceptions import BrickExecutionError
from bricks.core.loader import BlueprintLoader
from bricks.core.models import BrickMeta
from bricks.core.registry import BrickRegistry

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_registry_with(*fns: Any) -> BrickRegistry:
    """Create a registry with the given @brick-decorated functions."""
    reg = BrickRegistry()
    for fn in fns:
        bf = cast(BrickFunction, fn)
        reg.register(bf.__brick_meta__.name, bf, bf.__brick_meta__)
    return reg


def _run_single_step(fn: Any, params: dict[str, Any] | None = None) -> None:
    """Execute a single-step blueprint with the given function."""
    reg = _make_registry_with(fn)
    bf = cast(BrickFunction, fn)
    name = bf.__brick_meta__.name
    param_str = "\n".join(f"      {k}: {v!r}" for k, v in (params or {}).items())
    yaml = f"""
name: test_bp
steps:
  - name: step1
    brick: {name}
    params:
{param_str if param_str else "      x: 1"}
"""
    loader = BlueprintLoader()
    bp = loader.load_string(yaml)
    engine = BlueprintEngine(registry=reg)
    engine.run(bp)


# ── Test: BaseBrick teardown ───────────────────────────────────────────────────


class TestBaseBrickTeardown:
    def test_teardown_called_on_failure(self) -> None:
        """BaseBrick.teardown() is called when execute() raises."""
        teardown_calls: list[tuple[Any, Exception]] = []

        class FailingBrick(BaseBrick):
            """A brick that always fails."""

            class Meta:
                name = "failing_brick"

            def execute(self, inputs: BrickModel, metadata: BrickMeta) -> dict[str, Any]:
                raise RuntimeError("intentional failure")

            def teardown(self, inputs: BrickModel, metadata: BrickMeta, error: Exception) -> None:
                teardown_calls.append((inputs, error))

        brick_instance = FailingBrick()

        def wrapper(x: int) -> dict[str, Any]:
            """Wrapper delegating to FailingBrick."""
            return brick_instance.execute(BrickModel(), BrickMeta(name="failing_brick"))

        wrapper.__brick_meta__ = BrickMeta(name="failing_brick")  # type: ignore[attr-defined]
        wrapper.__brick_teardown__ = None  # type: ignore[attr-defined]

        reg = BrickRegistry()
        reg.register("failing_brick", wrapper, BrickMeta(name="failing_brick"))

        # Manually test BaseBrick.teardown() being called
        error = RuntimeError("test error")
        brick_instance.teardown(BrickModel(), BrickMeta(name="failing_brick"), error)
        assert len(teardown_calls) == 1
        assert teardown_calls[0][1] is error

    def test_teardown_default_is_noop(self) -> None:
        """BaseBrick.teardown() default implementation does nothing and doesn't raise."""

        class SimpleBrick(BaseBrick):
            """A simple no-op brick."""

            class Meta:
                name = "simple_brick"

            def execute(self, inputs: BrickModel, metadata: BrickMeta) -> dict[str, Any]:
                return {}

        brick_instance = SimpleBrick()
        # Should not raise
        brick_instance.teardown(BrickModel(), BrickMeta(name="simple_brick"), ValueError("test"))

    def test_teardown_signature(self) -> None:
        """BaseBrick.teardown() accepts (inputs, metadata, error)."""

        class TeardownBrick(BaseBrick):
            """Brick that captures teardown args."""

            class Meta:
                name = "teardown_brick"

            captured: ClassVar[list[tuple[BrickModel, BrickMeta, Exception]]] = []

            def execute(self, inputs: BrickModel, metadata: BrickMeta) -> dict[str, Any]:
                return {}

            def teardown(self, inputs: BrickModel, metadata: BrickMeta, error: Exception) -> None:
                TeardownBrick.captured.append((inputs, metadata, error))

        b = TeardownBrick()
        inputs = BrickModel()
        meta = BrickMeta(name="teardown_brick")
        err = ValueError("oops")
        b.teardown(inputs, meta, err)

        assert len(TeardownBrick.captured) == 1
        assert TeardownBrick.captured[0][2] is err


# ── Test: @brick teardown parameter ───────────────────────────────────────────


class TestBrickDecoratorTeardown:
    def test_teardown_param_stored(self) -> None:
        """@brick(teardown=fn) stores fn as __brick_teardown__."""
        teardown_calls: list[tuple[dict[str, Any], Exception]] = []

        def my_cleanup(inputs: dict[str, Any], error: Exception) -> None:
            teardown_calls.append((inputs, error))

        @brick(teardown=my_cleanup)
        def my_fn(x: int) -> int:
            """My fn."""
            return x

        bf = cast(BrickFunction, my_fn)
        assert bf.__brick_teardown__ is my_cleanup  # type: ignore[attr-defined]

    def test_teardown_none_by_default(self) -> None:
        """@brick without teardown= sets __brick_teardown__ to None."""

        @brick()
        def plain_fn(x: int) -> int:
            """Plain fn."""
            return x

        bf = cast(BrickFunction, plain_fn)
        assert bf.__brick_teardown__ is None  # type: ignore[attr-defined]

    def test_teardown_called_on_engine_failure(self) -> None:
        """Engine calls __brick_teardown__ when the step raises."""
        teardown_calls: list[tuple[dict[str, Any], Exception]] = []

        def my_cleanup(inputs: dict[str, Any], error: Exception) -> None:
            teardown_calls.append((inputs, error))

        @brick(teardown=my_cleanup)
        def always_fails(x: int) -> int:
            """Always fails."""
            raise RuntimeError("intentional failure")

        reg = _make_registry_with(always_fails)
        loader = BlueprintLoader()
        bp = loader.load_string("""
name: test_bp
steps:
  - name: s1
    brick: always_fails
    params:
      x: 42
""")
        engine = BlueprintEngine(registry=reg)

        with pytest.raises(BrickExecutionError):
            engine.run(bp)

        assert len(teardown_calls) == 1
        assert teardown_calls[0][0] == {"x": 42}
        assert isinstance(teardown_calls[0][1], RuntimeError)

    def test_no_teardown_no_error(self) -> None:
        """Engine doesn't crash when @brick has no teardown and a step fails."""

        @brick()
        def fails(x: int) -> int:
            """Fails."""
            raise ValueError("oops")

        reg = _make_registry_with(fails)
        loader = BlueprintLoader()
        bp = loader.load_string("""
name: test_bp
steps:
  - name: s1
    brick: fails
    params:
      x: 1
""")
        engine = BlueprintEngine(registry=reg)

        with pytest.raises(BrickExecutionError) as exc_info:
            engine.run(bp)

        # Original error preserved
        assert isinstance(exc_info.value.cause, ValueError)
        assert str(exc_info.value.cause) == "oops"


# ── Test: Engine teardown behavior ────────────────────────────────────────────


class TestEngineTeardown:
    def test_teardown_exception_does_not_mask_original(self) -> None:
        """If teardown raises, the original BrickExecutionError is still raised."""
        teardown_raised = False

        def bad_teardown(inputs: dict[str, Any], error: Exception) -> None:
            nonlocal teardown_raised
            teardown_raised = True
            raise RuntimeError("teardown also failed")

        @brick(teardown=bad_teardown)
        def fails(x: int) -> int:
            """Fails."""
            raise ValueError("original failure")

        reg = _make_registry_with(fails)
        loader = BlueprintLoader()
        bp = loader.load_string("""
name: test_bp
steps:
  - name: s1
    brick: fails
    params:
      x: 1
""")
        engine = BlueprintEngine(registry=reg)

        with pytest.raises(BrickExecutionError) as exc_info:
            engine.run(bp)

        # Original error preserved, teardown exception suppressed
        assert isinstance(exc_info.value.cause, ValueError)
        assert str(exc_info.value.cause) == "original failure"
        assert teardown_raised  # teardown was called

    def test_engine_calls_teardown_before_raising(self) -> None:
        """Engine calls teardown before raising BrickExecutionError."""
        order: list[str] = []

        def my_teardown(inputs: dict[str, Any], error: Exception) -> None:
            order.append("teardown")

        @brick(teardown=my_teardown)
        def fails(x: int) -> int:
            """Fails."""
            order.append("execute_failed")
            raise RuntimeError("fail")

        reg = _make_registry_with(fails)
        loader = BlueprintLoader()
        bp = loader.load_string("""
name: test_bp
steps:
  - name: s1
    brick: fails
    params:
      x: 1
""")
        engine = BlueprintEngine(registry=reg)

        with pytest.raises(BrickExecutionError):
            engine.run(bp)

        assert order == ["execute_failed", "teardown"]

    def test_reverse_teardown_of_completed_steps(self) -> None:
        """Engine reverse-teardowns all previously completed steps on failure."""
        teardown_order: list[str] = []

        def make_teardown(name: str) -> Any:
            def td(inputs: dict[str, Any], error: Exception) -> None:
                teardown_order.append(name)

            return td

        @brick(teardown=make_teardown("step1"))
        def step1(x: int) -> dict[str, int]:
            """Step 1."""
            return {"result": x + 1}

        @brick(teardown=make_teardown("step2"))
        def step2(result: int) -> dict[str, int]:
            """Step 2."""
            return {"result": result + 1}

        @brick(teardown=make_teardown("step3"))
        def step3(result: int) -> int:
            """Step 3 - always fails."""
            raise RuntimeError("step3 failed")

        reg = BrickRegistry()
        for fn in (step1, step2, step3):
            bf = cast(BrickFunction, fn)
            reg.register(bf.__brick_meta__.name, bf, bf.__brick_meta__)

        loader = BlueprintLoader()
        bp = loader.load_string("""
name: test_bp
steps:
  - name: s1
    brick: step1
    params:
      x: 1
    save_as: r1
  - name: s2
    brick: step2
    params:
      result: "${r1.result}"
    save_as: r2
  - name: s3
    brick: step3
    params:
      result: "${r2.result}"
""")
        engine = BlueprintEngine(registry=reg)

        with pytest.raises(BrickExecutionError):
            engine.run(bp)

        # step3 teardown first, then step2, then step1 (reverse order)
        assert teardown_order == ["step3", "step2", "step1"]
