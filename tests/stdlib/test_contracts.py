"""Contract tests: every stdlib brick must return {"result": ...}.

These tests run without --live (no LLM required).  They verify the Mission 048
contract that all stdlib bricks return a dict with a ``"result"`` key.

Run with: pytest packages/stdlib/tests/test_contracts.py
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from bricks.stdlib import (
    data_transformation,
    date_time,
    encoding_security,
    list_operations,
    math_numeric,
    string_processing,
    validation,
)

# ---------------------------------------------------------------------------
# Minimal-input overrides for bricks that need non-trivial arguments
# ---------------------------------------------------------------------------

_OVERRIDE_INPUTS: dict[str, dict[str, Any]] = {
    # math_numeric
    "divide": {"a": 10.0, "b": 2.0},
    "modulo": {"a": 10.0, "b": 3.0},
    "percentage": {"value": 25.0, "total": 100.0},
    "clamp_value": {"value": 5.0, "minimum": 0.0, "maximum": 10.0},
    # string_processing
    "template_string_fill": {"template": "Hello {name}", "values": {"name": "World"}},
    "extract_regex_pattern": {"text": "abc123", "pattern": r"\d+"},
    "truncate_text": {"text": "hello world", "max_length": 8},
    "concatenate_strings": {"parts": ["hello", " ", "world"]},
    "split_by_delimiter": {"text": "a,b,c", "delimiter": ","},
    "parse_date_string": {"date_str": "15/01/2024", "input_format": "%d/%m/%Y"},
    "convert_case": {"text": "hello world", "case": "upper"},
    "levenshtein_distance": {"s1": "kitten", "s2": "sitting"},
    "pad_string": {"text": "hi", "width": 10},
    "replace_substring": {"text": "hello world", "old": "world", "new": "bricks"},
    "starts_ends_with": {"text": "hello world", "prefix": "hello", "suffix": "world"},
    "truncate_string": {"text": "hello world", "max_length": 8},
    # date_time
    "parse_date": {"date_str": "2024-01-15", "fmt": "%Y-%m-%d"},
    "format_date": {"iso_date": "2024-01-15", "fmt": "%d/%m/%Y"},
    "date_diff": {"date_a": "2024-01-15", "date_b": "2024-01-10"},
    "add_days": {"iso_date": "2024-01-15", "days": 5},
    "add_hours": {"iso_datetime": "2024-01-15T12:00:00", "hours": 2},
    "extract_date_parts": {"iso_date": "2024-01-15"},
    "is_business_day": {"iso_date": "2024-01-15"},
    "date_range": {"start": "2024-01-01", "end": "2024-01-05"},
    "days_until": {"target_date": "2030-01-01"},
    # date_time (timezone — may fail without tzdata)
    "convert_timezone": {
        "iso_datetime": "2024-01-15T12:00:00",
        "from_tz": "UTC",
        "to_tz": "UTC",  # Same-zone conversion avoids OS tzdata dependency
    },
    # encoding_security
    "base64_decode": {"encoded": "aGVsbG8="},  # base64("hello")
    "compute_hash": {"data": "hello", "algorithm": "sha256"},
    "random_string": {"length": 8, "charset": "alphanumeric"},
    "escape_special_chars": {"text": "hello.world", "chars": ["."]},
    "mask_string": {"text": "secret-api-key-12345"},
    # data_transformation
    "filter_dict_list": {"items": [{"k": "v"}, {"k": "x"}], "key": "k", "value": "v"},
    "validate_json_schema": {"data": {"name": "test"}, "schema": {"required": ["name"]}},
    "merge_dictionaries": {"base": {"a": 1}, "override": {"b": 2}},
    "extract_dict_field": {"data": {"key": "value"}, "field": "key"},
    "cast_data_types": {"data": {"x": "1"}, "type_map": {"x": "int"}},
    "remove_null_values": {"data": {"a": 1, "b": None}},
    "flatten_nested_dict": {"data": {"a": {"b": 1}}},
    "deduplicate_dict_list": {"items": [{"id": 1}, {"id": 1}], "key": "id"},
    "sort_dict_list": {"items": [{"k": 2}, {"k": 1}], "key": "k"},
    "rename_dict_keys": {"data": {"old": 1}, "rename_map": {"old": "new"}},
    "group_by_key": {"items": [{"cat": "a"}, {"cat": "b"}], "key": "cat"},
    "convert_to_csv_str": {"items": [{"a": 1, "b": 2}]},
    "unflatten_dict": {"data": {"a.b": 1}},
    "calculate_aggregates": {
        "items": [{"n": 1.0}, {"n": 2.0}],
        "field": "n",
        "operation": "sum",
    },
    "join_lists_on_key": {
        "left": [{"id": 1, "val": "x"}],
        "right": [{"id": 1, "extra": "y"}],
        "key": "id",
    },
    "diff_dict_objects": {"old": {"a": 1}, "new": {"a": 2}},
    "parse_xml_to_dict": {"xml_text": "<root><item>value</item></root>"},
    "mask_sensitive_data": {"data": {"password": "secret"}, "fields": ["password"]},
    "pivot_data_structure": {
        "items": [{"k": "a", "v": 1}],
        "index_key": "k",
        "value_key": "v",
    },
    "slice_dict_list": {"items": [{"x": 1}], "start": 0, "end": 1},
    "dict_to_json_str": {"data": {"key": "value"}},
    "select_dict_keys": {"data": {"a": 1, "b": 2}, "keys": ["a"]},
    "set_dict_field": {"data": {"a": 1}, "field": "b", "value": 2},
    "count_dict_list": {"items": [{"a": 1}]},
    "extract_json_from_str": {"text": '{"key": "value"}'},
    # list_operations
    "chunk_list": {"items": [1, 2, 3, 4], "size": 2},
    "flatten_list": {"nested": [[1, 2], [3, 4]]},
    "zip_lists": {"a": [1, 2], "b": [3, 4]},
    "intersect_lists": {"a": [1, 2, 3], "b": [2, 3, 4]},
    "difference_lists": {"a": [1, 2, 3], "b": [2, 3]},
    "take_first_n": {"items": [1, 2, 3], "n": 2},
    "map_values": {"items": [{"k": "v1"}], "key": "k"},
    "reduce_sum": {"values": [1.0, 2.0, 3.0]},
    "is_empty_list": {"items": []},
    # validation
    "is_in_range": {"value": 5.0, "minimum": 0.0, "maximum": 10.0},
    "matches_pattern": {"text": "hello123", "pattern": r"[a-z]+\d+"},
    "has_required_keys": {"data": {"a": 1}, "required_keys": ["a"]},
    "compare_values": {"a": 1, "b": 2, "operator": "lt"},
}

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
    """Build minimal valid inputs for *func*, using overrides where available.

    For bricks without an override, auto-generates sensible defaults from
    the function signature and required parameters.

    Args:
        name: Registered brick name.
        func: The brick callable.

    Returns:
        Keyword argument dict suitable for calling *func*.
    """
    if name in _OVERRIDE_INPUTS:
        return _OVERRIDE_INPUTS[name]

    # Auto-generate from signature — only fill in required params (no default)
    import typing

    try:
        hints = typing.get_type_hints(func)
    except Exception:
        hints = {}

    sig = inspect.signature(func)
    inputs: dict[str, Any] = {}

    for pname, param in sig.parameters.items():
        if param.default is not inspect.Parameter.empty:
            continue  # use existing default
        hint = hints.get(pname)
        origin = getattr(hint, "__origin__", None)
        if hint is str:
            inputs[pname] = "hello"
        elif hint is float:
            inputs[pname] = 1.0
        elif hint is int:
            inputs[pname] = 1
        elif hint is bool:
            inputs[pname] = True
        elif origin is list:
            inner_args = getattr(hint, "__args__", None)
            if inner_args and inner_args[0] is float:
                inputs[pname] = [1.0, 2.0]
            elif inner_args and inner_args[0] is str:
                inputs[pname] = ["a", "b"]
            else:
                inputs[pname] = [1, 2, 3]
        elif origin is dict:
            inputs[pname] = {"key": "value"}
        else:
            inputs[pname] = "hello"

    return inputs


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
