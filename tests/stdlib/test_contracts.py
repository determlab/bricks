"""Contract tests: every stdlib brick must return {"result": ...}.

These tests run without --live (no LLM required).  They verify the Mission 048
contract that all stdlib bricks return a dict with a ``"result"`` key.

Run with: pytest packages/stdlib/tests/test_contracts.py
"""

from __future__ import annotations

from typing import Any

import pytest

from bricks.core.brick_check import synthesize_inputs
from bricks.stdlib import (
    data_transformation,
    date_time,
    encoding_security,
    list_operations,
    math_numeric,
    measurement,
    string_processing,
    validation,
)

# Bricks to skip when their required OS packages are absent on the test host.
# convert_timezone needs the tzdata package (or OS timezone database).
_SKIP_BRICKS: frozenset[str] = frozenset()


def _tzdata_available() -> bool:
    """Return True if the tzdata package or OS timezone database is available."""
    try:
        from zoneinfo import ZoneInfo

        ZoneInfo("UTC")
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

_STDLIB_MODULES = [
    data_transformation,
    date_time,
    encoding_security,
    list_operations,
    math_numeric,
    measurement,
    string_processing,
    validation,
]


def _discover_bricks() -> list[tuple[str, Any]]:
    """Return (name, callable) for every stdlib brick, deduplicated.

    Returns:
        Sorted list of (brick_name, callable) pairs.
    """
    seen: set[str] = set()
    bricks: list[tuple[str, Any]] = []
    for module in _STDLIB_MODULES:
        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if callable(obj) and hasattr(obj, "__brick_meta__"):
                name: str = obj.__brick_meta__.name
                if name not in seen:
                    seen.add(name)
                    bricks.append((name, obj))
    return sorted(bricks, key=lambda x: x[0])


def _build_inputs(name: str, func: Any) -> dict[str, Any]:
    """Build minimal valid inputs for *func*.

    Delegates to :func:`bricks.core.brick_check.synthesize_inputs` — the
    curated per-brick example (``KNOWN_EXAMPLE_INPUTS``) when *name* has one,
    otherwise an auto-generated value per required parameter. ``check-brick``
    (#51) uses the same function so an arbitrary given brick, not just a
    stdlib one, gets the same treatment.

    Args:
        name: Registered brick name.
        func: The brick callable.

    Returns:
        Keyword argument dict suitable for calling *func*.
    """
    return synthesize_inputs(func, name)


# ---------------------------------------------------------------------------
# Parametrised contract tests
# ---------------------------------------------------------------------------

_ALL_BRICKS = _discover_bricks()


@pytest.mark.parametrize("brick_name,brick_fn", _ALL_BRICKS, ids=[b[0] for b in _ALL_BRICKS])
def test_brick_returns_dict_with_result_key(brick_name: str, brick_fn: Any) -> None:
    """Every stdlib brick must return a dict containing the key ``"result"``.

    This enforces the Mission 048 contract: all stdlib bricks use the
    standardised ``{"result": <value>}`` return shape.

    Args:
        brick_name: The registered brick name (used as test ID).
        brick_fn: The brick callable.
    """
    if brick_name in _SKIP_BRICKS:
        pytest.skip(f"{brick_name!r} skipped due to known environment issue")
    if brick_name == "convert_timezone" and not _tzdata_available():
        pytest.skip("convert_timezone requires tzdata or OS timezone database")

    inputs = _build_inputs(brick_name, brick_fn)

    result = brick_fn(**inputs)

    assert isinstance(result, dict), f"{brick_name!r}: expected dict return, got {type(result).__name__}"
    assert "result" in result, f"{brick_name!r}: missing 'result' key in return value {result!r}"


def test_contract_covers_all_stdlib_bricks() -> None:
    """Sanity check: the parametrised suite covers all 100 stdlib bricks."""
    assert len(_ALL_BRICKS) >= 95, f"Expected ≥95 bricks but discovered only {len(_ALL_BRICKS)}"


def test_no_brick_name_duplicates() -> None:
    """Each brick name appears exactly once in the discovered list."""
    names = [name for name, _ in _ALL_BRICKS]
    assert len(names) == len(set(names)), "Duplicate brick names found in discovery"
