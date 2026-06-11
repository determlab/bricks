"""Engine-boundary error attribution for wrapper primitives.

Guards the contract from issue #34 / #36: when any of the wrapping
primitives (``__for_each__``, ``__branch__``, sub-blueprint steps)
invokes an inner brick that raises, the top-level
``BrickExecutionError`` must name **the real failing brick** — not the
wrapper — and the ``__cause__`` chain must contain exactly one
``BrickExecutionError`` (no double-wrapping).

The sister module ``tests/core/test_builtin_error_attribution.py``
covers the same invariant case-by-case; this file consolidates the
contract as a single parametrised suite plus the cases the other file
cannot reach (sub-blueprint, nested for_each inside branch).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from bricks.core.builtins import register_builtins
from bricks.core.engine import BlueprintEngine
from bricks.core.exceptions import BrickExecutionError
from bricks.core.models import BlueprintDefinition, BrickMeta, StepDefinition
from bricks.core.registry import BrickRegistry

_INNER_MARKER = "will_fail"


def _make_registry() -> BrickRegistry:
    reg = BrickRegistry()
    register_builtins(reg)

    def will_fail(item: Any = None, input: Any = None) -> dict[str, Any]:
        """Raises on every call. Accepts ``item`` (for_each) or ``input``
        (branch) so either wrapper can invoke it."""
        tag = item if item is not None else input
        raise RuntimeError(f"inner blew up on {tag!r}")

    reg.register(_INNER_MARKER, will_fail, BrickMeta(name=_INNER_MARKER, description="always fails"))

    def true_condition(input: Any) -> dict[str, Any]:
        return {"result": True}

    reg.register("true_condition", true_condition, BrickMeta(name="true_condition", description="True"))

    def false_condition(input: Any) -> dict[str, Any]:
        return {"result": False}

    reg.register("false_condition", false_condition, BrickMeta(name="false_condition", description="False"))

    return reg


def _assert_attribution(exc: BrickExecutionError) -> None:
    """Shared invariants: attribution + no double-wrap."""
    assert exc.brick_name == _INNER_MARKER, f"expected brick_name={_INNER_MARKER!r}, got {exc.brick_name!r}"
    assert isinstance(exc.cause, RuntimeError), f"expected RuntimeError cause, got {type(exc.cause)!r}"

    # Walk the __cause__ chain; exactly one BEE must appear.
    count = 0
    cur: BaseException | None = exc
    while cur is not None:
        if isinstance(cur, BrickExecutionError):
            count += 1
        cur = cur.__cause__
    assert count == 1, f"expected exactly one BrickExecutionError in cause chain, got {count}"


# ── parametrised wrapper coverage ───────────────────────────────────────────


@pytest.fixture(name="engine")
def _engine() -> BlueprintEngine:
    return BlueprintEngine(registry=_make_registry())


def _make_step(brick: str, params: dict[str, Any]) -> BlueprintDefinition:
    return BlueprintDefinition(
        name="attribution_probe",
        steps=[StepDefinition(name="probe", brick=brick, params=params)],
    )


_WRAPPER_CASES: list[tuple[str, str, dict[str, Any]]] = [
    (
        "for_each_fail",
        "__for_each__",
        {"items": [1, 2], "do_brick": _INNER_MARKER, "on_error": "fail"},
    ),
    (
        "branch_if_true",
        "__branch__",
        {"condition_brick": "true_condition", "condition_input": 1, "if_true_brick": _INNER_MARKER},
    ),
    (
        "branch_if_false",
        "__branch__",
        {
            "condition_brick": "false_condition",
            "condition_input": 1,
            "if_false_brick": _INNER_MARKER,
        },
    ),
    (
        "branch_condition_itself_fails",
        "__branch__",
        {"condition_brick": _INNER_MARKER, "condition_input": 1, "if_true_brick": "true_condition"},
    ),
]


@pytest.mark.parametrize(("case_id", "brick", "params"), _WRAPPER_CASES, ids=[c[0] for c in _WRAPPER_CASES])
def test_wrapper_surfaces_inner_brick_name(
    case_id: str,
    brick: str,
    params: dict[str, Any],
    engine: BlueprintEngine,
) -> None:
    with pytest.raises(BrickExecutionError) as exc_info:
        engine.run(_make_step(brick, params))

    _assert_attribution(exc_info.value)


# ── for_each collect mode — not a raise, but traces must carry the name ────


def test_for_each_collect_mode_error_records_inner_brick_name(engine: BlueprintEngine) -> None:
    """In collect mode, ``__for_each__`` swallows exceptions and records
    strings. Each recorded string must begin with the real inner brick
    name so log-scraping tooling can still attribute failures."""
    bp = BlueprintDefinition(
        name="collect_probe",
        steps=[
            StepDefinition(
                name="loop",
                brick="__for_each__",
                params={"items": [1, 2, 3], "do_brick": _INNER_MARKER, "on_error": "collect"},
                save_as="loop",
            )
        ],
        outputs_map={"result": "${loop}"},
    )

    out = engine.run(bp).outputs

    errors = out["result"]["errors"]
    assert len(errors) == 3
    for err in errors:
        assert err["error"].startswith(f"{_INNER_MARKER}:"), f"missing inner-brick prefix: {err!r}"


# ── nested: for_each inside a branch arm — attribution must still reach ─────


def test_nested_for_each_inside_branch_surfaces_innermost_brick(engine: BlueprintEngine) -> None:
    """A ``__for_each__`` nested inside a ``__branch__`` arm whose inner
    brick raises must attribute to the innermost brick — wrappers on both
    levels pass it through."""
    reg = engine._registry

    # Inner wrapper brick: receives a single item from the outer for_each and
    # runs an inner for_each over a list containing that item, calling
    # will_fail on each.
    def nested_wrapper(item: Any) -> dict[str, Any]:
        inner_callable, _ = reg.get(_INNER_MARKER)
        inner_callable(item=item)  # raises RuntimeError → BEE via builtin wrapping
        return {"result": None}  # unreachable

    reg.register(
        "nested_wrapper",
        nested_wrapper,
        BrickMeta(name="nested_wrapper", description="invokes will_fail"),
    )

    bp = BlueprintDefinition(
        name="nested_probe",
        steps=[
            StepDefinition(
                name="outer",
                brick="__for_each__",
                params={"items": [1], "do_brick": "nested_wrapper", "on_error": "fail"},
            )
        ],
    )

    with pytest.raises(BrickExecutionError) as exc_info:
        engine.run(bp)

    # The **outer** ``__for_each__`` re-wraps with brick_name=nested_wrapper.
    # That is the correct contract: attribute to the brick the wrapper
    # actually invoked, not the deepest leaf. What must not happen is
    # ``__for_each__`` ending up as the brick_name.
    assert exc_info.value.brick_name == "nested_wrapper"
    assert exc_info.value.brick_name != "__for_each__"
    # And exactly one BEE in the chain — no double-wrapping.
    count = sum(1 for e in _walk_causes(exc_info.value) if isinstance(e, BrickExecutionError))
    assert count == 1


# ── sub-blueprint — loaded from disk, inner step failure must pass through ──


def test_sub_blueprint_inner_failure_surfaces_real_brick_name(tmp_path: Path) -> None:
    """``_execute_sub_blueprint_step`` already has the pass-through arm; this
    test guards it. An inner step failure inside a child blueprint loaded
    from disk must surface with the inner brick name, not the child
    blueprint path."""
    reg = _make_registry()

    # Child blueprint: one step calling will_fail.
    child_yaml = tmp_path / "child.yaml"
    child_yaml.write_text(
        "\n".join(
            [
                "name: child",
                "steps:",
                "  - name: inner",
                f"    brick: {_INNER_MARKER}",
                "    params:",
                "      item: 42",
            ]
        ),
        encoding="utf-8",
    )

    parent = BlueprintDefinition(
        name="parent",
        steps=[StepDefinition(name="call_child", blueprint=str(child_yaml))],
    )
    engine = BlueprintEngine(registry=reg)

    with pytest.raises(BrickExecutionError) as exc_info:
        engine.run(parent)

    _assert_attribution(exc_info.value)


# ── helper ─────────────────────────────────────────────────────────────────


def _walk_causes(exc: BaseException) -> list[BaseException]:
    out: list[BaseException] = []
    cur: BaseException | None = exc
    while cur is not None:
        out.append(cur)
        cur = cur.__cause__
    return out
