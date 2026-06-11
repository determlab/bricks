"""Tests for issue #60 part 2 — `for_each` extraction failures must self-report.

When the ``for_each`` lambda doesn't record a step node through the
tracer, the resulting ``ValueError`` is the only breadcrumb the caller
has to diagnose. Pre-fix, it said only ``"could not extract brick name
from do= callable"`` — no source, no original exception, forcing an
expensive re-run with a debugger attached. This suite guards the
widened error message.
"""

from __future__ import annotations

import pytest

from bricks.core.dsl import for_each, step


def test_empty_lambda_reports_lambda_source() -> None:
    """A lambda that simply doesn't call ``step.X(...)`` must trigger the
    extraction error with the lambda's source included — so the reader
    can see the shape immediately."""
    with pytest.raises(ValueError) as exc_info:
        for_each(items=[1, 2, 3], do=lambda _x: None)  # doesn't record anything

    msg = str(exc_info.value)
    assert "could not extract brick name" in msg
    # `inspect.getsource` on a lambda typically returns the whole enclosing
    # line; any fragment uniquely identifying this lambda is good enough.
    assert "lambda _x: None" in msg, f"lambda source not surfaced: {msg!r}"


def test_lambda_raising_before_step_call_reports_inner_exception() -> None:
    """A lambda that raises *before* recording a step call must surface
    the inner exception type + message — pre-fix we silently swallowed it."""

    def blow_up_first(_x: object) -> object:
        raise RuntimeError("synthetic failure inside lambda")

    with pytest.raises(ValueError) as exc_info:
        # The ``do`` lambda raises before the ``step.X(...)`` call, so
        # the tracer never records a node. The error must mention the
        # RuntimeError so the reader knows *why* the trace was empty.
        for_each(items=[1, 2], do=lambda x: blow_up_first(x) or step.nothing(item=x))

    msg = str(exc_info.value)
    assert "could not extract brick name" in msg
    assert "RuntimeError" in msg
    assert "synthetic failure inside lambda" in msg
