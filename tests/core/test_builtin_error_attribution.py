"""Regression tests for issue #34 — ``BrickExecutionError.brick_name`` must
point at the real failing inner brick when a `for_each`/`branch` primitive
invokes it, not at the ``__for_each__`` / ``__branch__`` wrapper.
"""

from __future__ import annotations

from typing import Any

import pytest

from bricks.core.builtins import register_builtins
from bricks.core.engine import BlueprintEngine
from bricks.core.exceptions import BrickExecutionError
from bricks.core.models import BlueprintDefinition, BrickMeta, StepDefinition
from bricks.core.registry import BrickRegistry

# ── shared fixtures ──────────────────────────────────────────────────────────


def _make_registry() -> BrickRegistry:
    """Registry with builtins + a family of real/failing stdlib-style bricks."""
    reg = BrickRegistry()
    register_builtins(reg)

    def is_email_valid(email: str) -> dict[str, Any]:
        """Valid iff the string contains '@'. The signature deliberately takes
        ``email`` (not ``item``) so a for_each with the wrong kwarg name will
        fail with the exact repro TypeError from issue #34."""
        return {"result": "@" in email}

    reg.register("is_email_valid", is_email_valid, BrickMeta(name="is_email_valid", description="validate email"))

    def boom_at_runtime(item: Any) -> dict[str, Any]:
        """Accepts ``item`` but always raises at runtime."""
        raise RuntimeError(f"boom: {item!r}")

    reg.register("boom_at_runtime", boom_at_runtime, BrickMeta(name="boom_at_runtime", description="always fails"))

    def always_true(input: Any) -> dict[str, Any]:
        return {"result": True}

    reg.register("always_true", always_true, BrickMeta(name="always_true", description="condition=True"))

    def boom_condition(input: Any) -> dict[str, Any]:
        raise RuntimeError("condition exploded")

    reg.register("boom_condition", boom_condition, BrickMeta(name="boom_condition", description="failing condition"))

    def boom_true_branch(input: Any) -> dict[str, Any]:
        raise RuntimeError("if_true exploded")

    reg.register("boom_true_branch", boom_true_branch, BrickMeta(name="boom_true_branch", description="failing true"))

    def boom_false_branch(input: Any) -> dict[str, Any]:
        raise RuntimeError("if_false exploded")

    reg.register(
        "boom_false_branch",
        boom_false_branch,
        BrickMeta(name="boom_false_branch", description="failing false"),
    )

    def plain_fail(x: int) -> dict[str, Any]:
        raise ValueError("top-level brick failure")

    reg.register("plain_fail", plain_fail, BrickMeta(name="plain_fail", description="regression guard"))

    return reg


@pytest.fixture(name="registry")
def _registry_fixture() -> BrickRegistry:
    return _make_registry()


def _run_for_each(
    engine: BlueprintEngine,
    items: list[Any],
    do_brick: str,
    on_error: str = "fail",
) -> dict[str, Any]:
    bp = BlueprintDefinition(
        name="for_each_test",
        steps=[
            StepDefinition(
                name="loop",
                brick="__for_each__",
                params={"items": items, "do_brick": do_brick, "on_error": on_error},
                save_as="loop_result",
            )
        ],
        outputs_map={"result": "${loop_result}"},
    )
    return engine.run(bp).outputs


def _run_branch(
    engine: BlueprintEngine,
    condition_brick: str,
    if_true_brick: str = "",
    if_false_brick: str = "",
    condition_input: Any = 1,
) -> dict[str, Any]:
    bp = BlueprintDefinition(
        name="branch_test",
        steps=[
            StepDefinition(
                name="routing",
                brick="__branch__",
                params={
                    "condition_brick": condition_brick,
                    "condition_input": condition_input,
                    "if_true_brick": if_true_brick,
                    "if_false_brick": if_false_brick,
                },
                save_as="branch_result",
            )
        ],
        outputs_map={"result": "${branch_result}"},
    )
    return engine.run(bp).outputs


# ── for_each attribution ─────────────────────────────────────────────────────


def test_for_each_wrong_kwarg_reports_real_inner_brick(registry: BrickRegistry) -> None:
    """The repro from issue #34: inner brick expects ``email``, for_each
    passes ``item=``. The engine surfaces ``brick_name="is_email_valid"``."""
    engine = BlueprintEngine(registry=registry)
    with pytest.raises(BrickExecutionError) as exc_info:
        _run_for_each(engine, items=["a@b.com", "not-an-email"], do_brick="is_email_valid")

    assert exc_info.value.brick_name == "is_email_valid"
    assert exc_info.value.brick_name != "__for_each__"
    # step_name carries the per-item suffix from the builtin, plus the engine
    # keeps whichever step it raised in; the key invariant is brick_name.
    assert "is_email_valid" in exc_info.value.step_name


def test_for_each_inner_runtime_error_reports_real_inner_brick(registry: BrickRegistry) -> None:
    engine = BlueprintEngine(registry=registry)
    with pytest.raises(BrickExecutionError) as exc_info:
        _run_for_each(engine, items=[1, 2], do_brick="boom_at_runtime")

    assert exc_info.value.brick_name == "boom_at_runtime"


def test_for_each_collect_mode_tags_errors_with_inner_name(registry: BrickRegistry) -> None:
    """In ``on_error='collect'`` mode no exception propagates, but each
    collected error string names the real inner brick so traces remain
    attributable."""
    engine = BlueprintEngine(registry=registry)
    out = _run_for_each(engine, items=[1, 2], do_brick="boom_at_runtime", on_error="collect")

    loop = out["result"]
    assert len(loop["errors"]) == 2
    for err in loop["errors"]:
        assert err["error"].startswith("boom_at_runtime:"), err


# ── branch attribution ──────────────────────────────────────────────────────


def test_branch_failing_condition_reports_condition_brick(registry: BrickRegistry) -> None:
    engine = BlueprintEngine(registry=registry)
    with pytest.raises(BrickExecutionError) as exc_info:
        _run_branch(engine, condition_brick="boom_condition", if_true_brick="always_true")

    assert exc_info.value.brick_name == "boom_condition"


def test_branch_failing_if_true_arm_reports_if_true_brick(registry: BrickRegistry) -> None:
    engine = BlueprintEngine(registry=registry)
    with pytest.raises(BrickExecutionError) as exc_info:
        _run_branch(engine, condition_brick="always_true", if_true_brick="boom_true_branch")

    assert exc_info.value.brick_name == "boom_true_branch"


def test_branch_failing_if_false_arm_reports_if_false_brick(registry: BrickRegistry) -> None:
    """condition_brick returns True only when input>0; passing 0 routes false."""

    def always_false(input: Any) -> dict[str, Any]:
        return {"result": False}

    registry.register("always_false", always_false, BrickMeta(name="always_false", description="False"))
    engine = BlueprintEngine(registry=registry)

    with pytest.raises(BrickExecutionError) as exc_info:
        _run_branch(engine, condition_brick="always_false", if_false_brick="boom_false_branch")

    assert exc_info.value.brick_name == "boom_false_branch"


# ── regression guards ──────────────────────────────────────────────────────


def test_plain_brick_failure_still_attributes_correctly(registry: BrickRegistry) -> None:
    """Top-level `step.X()` failures must still surface as ``brick_name="X"``
    — the fix must not regress the non-for_each / non-branch path."""
    engine = BlueprintEngine(registry=registry)
    bp = BlueprintDefinition(
        name="plain",
        steps=[StepDefinition(name="s1", brick="plain_fail", params={"x": 1})],
    )
    with pytest.raises(BrickExecutionError) as exc_info:
        engine.run(bp)

    assert exc_info.value.brick_name == "plain_fail"
    assert isinstance(exc_info.value.cause, ValueError)


def test_no_double_wrapping_on_for_each_failure(registry: BrickRegistry) -> None:
    """Exactly one ``BrickExecutionError`` in the cause chain — the outer
    engine wrapper must not re-wrap the inner-wrapped exception."""
    engine = BlueprintEngine(registry=registry)
    with pytest.raises(BrickExecutionError) as exc_info:
        _run_for_each(engine, items=[1], do_brick="boom_at_runtime")

    # Walk the __cause__ chain and count BEEs.
    count = 0
    cur: BaseException | None = exc_info.value
    while cur is not None:
        if isinstance(cur, BrickExecutionError):
            count += 1
        cur = cur.__cause__
    assert count == 1, f"expected exactly one BrickExecutionError in cause chain, got {count}"
