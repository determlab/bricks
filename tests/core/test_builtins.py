"""Tests for built-in DSL bricks (__for_each__, __branch__) and register_builtins."""

from __future__ import annotations

from typing import Any

import pytest

from bricks.core.builtins import register_builtins
from bricks.core.models import BrickMeta
from bricks.core.registry import BrickRegistry

# ---------------------------------------------------------------------------
# Registry fixtures
# ---------------------------------------------------------------------------


def _make_registry() -> BrickRegistry:
    """Create a registry with builtins + simple test bricks registered."""
    reg = BrickRegistry()
    register_builtins(reg)

    # Simple double brick
    def double(item: Any) -> dict[str, Any]:
        """Double the input."""
        return {"result": item * 2}

    reg.register("double", double, BrickMeta(name="double", description="Double the input"))

    # Brick that always raises
    def fail_always(item: Any) -> dict[str, Any]:
        """Always fails."""
        raise RuntimeError(f"fail on {item!r}")

    reg.register("fail_always", fail_always, BrickMeta(name="fail_always", description="Always fails"))

    # Condition brick — returns True if item > 0
    def is_positive(input: Any) -> dict[str, Any]:
        """Return True if input > 0."""
        return {"result": bool(input and input > 0)}

    reg.register("is_positive", is_positive, BrickMeta(name="is_positive", description="Check positive"))

    # True branch brick
    def positive_label(input: Any) -> dict[str, Any]:
        """Label as positive."""
        return {"label": "positive", "value": input}

    reg.register("positive_label", positive_label, BrickMeta(name="positive_label", description="Label positive"))

    # False branch brick
    def negative_label(input: Any) -> dict[str, Any]:
        """Label as negative."""
        return {"label": "negative", "value": input}

    reg.register("negative_label", negative_label, BrickMeta(name="negative_label", description="Label negative"))

    return reg


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


def test_for_each_brick_registered() -> None:
    """__for_each__ exists in BrickRegistry after register_builtins."""
    reg = BrickRegistry()
    register_builtins(reg)
    assert reg.has("__for_each__")


def test_branch_brick_registered() -> None:
    """__branch__ exists in BrickRegistry after register_builtins."""
    reg = BrickRegistry()
    register_builtins(reg)
    assert reg.has("__branch__")


def test_builtins_hidden_from_catalog() -> None:
    """list_public() does not include __for_each__ or __branch__."""
    reg = BrickRegistry()
    register_builtins(reg)
    public_names = {name for name, _ in reg.list_public()}
    assert "__for_each__" not in public_names
    assert "__branch__" not in public_names


def test_register_builtins_idempotent() -> None:
    """Calling register_builtins twice does not raise DuplicateBrickError."""
    reg = BrickRegistry()
    register_builtins(reg)
    register_builtins(reg)  # second call should be a no-op
    assert reg.has("__for_each__")


# ---------------------------------------------------------------------------
# __for_each__ execution tests
# ---------------------------------------------------------------------------


def test_for_each_executes_over_list() -> None:
    """__for_each__ with a simple brick and 3-item list returns 3 results."""
    reg = _make_registry()
    callable_, _ = reg.get("__for_each__")
    result = callable_(items=[1, 2, 3], do_brick="double")
    assert result["results"] == [{"result": 2}, {"result": 4}, {"result": 6}]


def test_for_each_fail_mode_stops_on_error() -> None:
    """__for_each__ in fail mode raises on first error, attributed to the
    real inner brick (issue #34) rather than to ``__for_each__``."""
    from bricks.core.exceptions import BrickExecutionError

    reg = _make_registry()
    callable_, _ = reg.get("__for_each__")
    with pytest.raises(BrickExecutionError) as exc_info:
        callable_(items=[1, 2, 3], do_brick="fail_always", on_error="fail")

    assert exc_info.value.brick_name == "fail_always"
    assert isinstance(exc_info.value.cause, RuntimeError)


def test_for_each_collect_mode_gathers_errors() -> None:
    """__for_each__ in collect mode processes all items and gathers errors."""
    reg = _make_registry()
    callable_, _ = reg.get("__for_each__")
    result = callable_(items=[1, 2, 3], do_brick="fail_always", on_error="collect")
    assert len(result["errors"]) == 3
    assert result["results"] == [None, None, None]


def test_for_each_collect_returns_results_and_errors() -> None:
    """Output of collect mode has both 'results' and 'errors' keys."""
    reg = _make_registry()
    callable_, _ = reg.get("__for_each__")
    result = callable_(items=[1], do_brick="fail_always", on_error="collect")
    assert "results" in result
    assert "errors" in result


# ---------------------------------------------------------------------------
# __branch__ execution tests
# ---------------------------------------------------------------------------


def test_branch_true_path() -> None:
    """__branch__: condition returns True → if_true_brick is executed."""
    reg = _make_registry()
    callable_, _ = reg.get("__branch__")
    result = callable_(
        condition_brick="is_positive",
        condition_input=5,
        if_true_brick="positive_label",
        if_false_brick="negative_label",
    )
    assert result["label"] == "positive"
    assert result["branch_taken"] == "true"


def test_branch_false_path() -> None:
    """__branch__: condition returns False → if_false_brick is executed."""
    reg = _make_registry()
    callable_, _ = reg.get("__branch__")
    result = callable_(
        condition_brick="is_positive",
        condition_input=-1,
        if_true_brick="positive_label",
        if_false_brick="negative_label",
    )
    assert result["label"] == "negative"
    assert result["branch_taken"] == "false"


def test_branch_output_includes_branch_taken() -> None:
    """__branch__ output always has 'branch_taken' key."""
    reg = _make_registry()
    callable_, _ = reg.get("__branch__")
    result = callable_(
        condition_brick="is_positive",
        condition_input=1,
        if_true_brick="positive_label",
        if_false_brick="negative_label",
    )
    assert "branch_taken" in result
