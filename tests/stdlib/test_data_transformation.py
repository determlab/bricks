"""Tests for bricks/stdlib/data_transformation.py — 25 tests."""

from __future__ import annotations

import pytest

from bricks.stdlib.data_transformation import (
    calculate_aggregates,
    cast_data_types,
    convert_to_csv_str,
    count_dict_list,
    deduplicate_dict_list,
    dict_to_json_str,
    diff_dict_objects,
    extract_dict_field,
    extract_json_from_str,
    filter_dict_list,
    flatten_nested_dict,
    group_by_key,
    join_lists_on_key,
    mask_sensitive_data,
    merge_dictionaries,
    parse_xml_to_dict,
    pivot_data_structure,
    remove_null_values,
    rename_dict_keys,
    select_dict_keys,
    set_dict_field,
    slice_dict_list,
    sort_dict_list,
    unflatten_dict,
    validate_json_schema,
)


def test_extract_json_from_str_plain_json() -> None:
    assert extract_json_from_str('{"a": 1}')["result"] == {"a": 1}


def test_extract_json_from_str_with_fence() -> None:
    text = '```json\n{"x": 42}\n```'
    assert extract_json_from_str(text)["result"] == {"x": 42}


def test_filter_dict_list_filters_by_value() -> None:
    items = [{"status": "active"}, {"status": "inactive"}]
    assert filter_dict_list(items, "status", "active")["result"] == [{"status": "active"}]


def test_validate_json_schema_all_required_present() -> None:
    assert validate_json_schema({"a": 1, "b": 2}, {"required": ["a", "b"]})["result"] is True


def test_validate_json_schema_missing_key() -> None:
    assert validate_json_schema({"a": 1}, {"required": ["a", "b"]})["result"] is False


def test_merge_dictionaries_override_wins() -> None:
    result = merge_dictionaries({"a": 1, "b": 2}, {"b": 99})["result"]
    assert result == {"a": 1, "b": 99}


def test_extract_dict_field_returns_value() -> None:
    assert extract_dict_field({"key": "val"}, "key")["result"] == "val"


def test_cast_data_types_int_cast() -> None:
    result = cast_data_types({"n": "42"}, {"n": "int"})["result"]
    assert result["n"] == 42


def test_remove_null_values_removes_nones() -> None:
    result = remove_null_values({"a": 1, "b": None})["result"]
    assert "b" not in result and "a" in result


def test_flatten_nested_dict_flattens() -> None:
    result = flatten_nested_dict({"a": {"b": 1}})["result"]
    assert result == {"a.b": 1}


def test_deduplicate_dict_list_first_wins() -> None:
    items = [{"id": 1, "v": "first"}, {"id": 1, "v": "second"}]
    result = deduplicate_dict_list(items, "id")["result"]
    assert len(result) == 1 and result[0]["v"] == "first"


def test_sort_dict_list_ascending() -> None:
    items = [{"n": 3}, {"n": 1}, {"n": 2}]
    result = sort_dict_list(items, "n")["result"]
    assert [r["n"] for r in result] == [1, 2, 3]


def test_rename_dict_keys_renames() -> None:
    result = rename_dict_keys({"old": 1}, {"old": "new"})["result"]
    assert "new" in result and "old" not in result


def test_group_by_key_groups() -> None:
    items = [{"t": "a"}, {"t": "b"}, {"t": "a"}]
    result = group_by_key(items, "t")["result"]
    assert len(result["a"]) == 2


def test_convert_to_csv_str_has_header() -> None:
    items = [{"name": "Alice", "age": 30}]
    csv = convert_to_csv_str(items)["result"]
    assert "name" in csv and "Alice" in csv


def test_unflatten_dict_restores_nesting() -> None:
    result = unflatten_dict({"a.b": 1})["result"]
    assert result == {"a": {"b": 1}}


def test_calculate_aggregates_sum() -> None:
    items = [{"v": 1}, {"v": 2}, {"v": 3}]
    assert calculate_aggregates(items, "v", "sum")["result"] == pytest.approx(6.0)


def test_calculate_aggregates_unknown_op_raises() -> None:
    with pytest.raises(ValueError):
        calculate_aggregates([{"v": 1}], "v", "median")


def test_join_lists_on_key_inner_join() -> None:
    left = [{"id": 1, "name": "Alice"}]
    right = [{"id": 1, "role": "admin"}]
    result = join_lists_on_key(left, right, "id")["result"]
    assert result[0]["name"] == "Alice" and result[0]["role"] == "admin"


def test_diff_dict_objects_detects_changes() -> None:
    diff = diff_dict_objects({"a": 1}, {"a": 2})["result"]
    assert "a" in diff["changed"]


def test_parse_xml_to_dict_parses_element() -> None:
    xml = "<root><item>hello</item></root>"
    result = parse_xml_to_dict(xml)["result"]
    assert result["root"]["item"] == "hello"


def test_mask_sensitive_data_masks_fields() -> None:
    result = mask_sensitive_data({"password": "secret", "name": "Alice"}, ["password"])["result"]
    assert result["password"] == "***" and result["name"] == "Alice"  # noqa: S105


def test_pivot_data_structure_pivots() -> None:
    items = [{"k": "a", "v": 1}, {"k": "b", "v": 2}]
    result = pivot_data_structure(items, "k", "v")["result"]
    assert result == {"a": 1, "b": 2}


def test_slice_dict_list_slices() -> None:
    items = [{"i": 0}, {"i": 1}, {"i": 2}]
    assert slice_dict_list(items, 1, 3)["result"] == [{"i": 1}, {"i": 2}]


def test_dict_to_json_str_serializes() -> None:
    result = dict_to_json_str({"a": 1})["result"]
    assert '"a"' in result


def test_select_dict_keys_returns_subset() -> None:
    result = select_dict_keys({"a": 1, "b": 2, "c": 3}, ["a", "c"])["result"]
    assert result == {"a": 1, "c": 3}


def test_set_dict_field_adds_field() -> None:
    result = set_dict_field({"a": 1}, "b", 2)["result"]
    assert result == {"a": 1, "b": 2}


def test_count_dict_list_returns_count() -> None:
    assert count_dict_list([{}, {}, {}])["result"] == 3
