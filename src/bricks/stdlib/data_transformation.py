"""Data Transformation bricks — 25 bricks for JSON, CSV, XML, and dict operations."""

from __future__ import annotations

import csv
import io
import json
import xml.etree.ElementTree as ET
from typing import Any, Literal

from bricks.core.brick import brick


@brick(tags=["data", "json", "parsing"], category="data_transformation", destructive=False)
def extract_json_from_str(text: str) -> dict[str, Any]:
    """Extract JSON from a string, stripping markdown code fences if present. Returns {result: parsed}.

    Args:
        text: String containing JSON, optionally wrapped in markdown fences.

    Returns:
        dict with key ``result`` containing the parsed JSON value.

    Raises:
        ValueError: If no valid JSON is found.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        # strip opening fence line and closing fence
        inner = "\n".join(lines[1:-1]) if lines[-1].strip().startswith("```") else "\n".join(lines[1:])
        cleaned = inner.strip()
    return {"result": json.loads(cleaned)}


@brick(tags=["data", "filter", "list"], category="data_transformation", destructive=False)
def filter_dict_list(items: list[dict[str, Any]], key: str, value: Any) -> dict[str, list[dict[str, Any]]]:
    """Filter a list of dicts keeping only items where items[key] == value. Returns {result: filtered}.

    Args:
        items: List of dicts to filter.
        key: Dict key to test.
        value: Value to match (equality check).

    Returns:
        dict with key ``result`` containing matching dicts.
    """
    return {"result": [item for item in items if item.get(key) == value]}


@brick(tags=["data", "validation", "schema"], category="data_transformation", destructive=False)
def validate_json_schema(data: dict[str, Any], schema: dict[str, Any]) -> dict[str, bool]:
    """Validate that data contains all required keys defined in schema. Returns {result: bool}.

    Args:
        data: The dict to validate.
        schema: Dict with a ``required`` list of key names.

    Returns:
        dict with key ``result`` — True if all required keys are present.
    """
    required = schema.get("required", [])
    valid = all(k in data for k in required)
    return {"result": valid}


@brick(tags=["data", "merge", "dict"], category="data_transformation", destructive=False)
def merge_dictionaries(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge two dicts; override values take precedence. Returns {result: merged}.

    Args:
        base: The base dictionary.
        override: Keys from this dict overwrite base.

    Returns:
        dict with key ``result`` containing the merged dict.
    """
    return {"result": {**base, **override}}


@brick(tags=["data", "extraction", "dict"], category="data_transformation", destructive=False)
def extract_dict_field(data: dict[str, Any], field: str) -> dict[str, Any]:
    """Extract a single field from a dict. Returns {result: field_value}.

    Args:
        data: Source dictionary.
        field: Key to extract.

    Returns:
        dict with key ``result`` containing the field value, or None if missing.
    """
    return {"result": data.get(field)}


@brick(tags=["data", "casting", "types"], category="data_transformation", destructive=False)
def cast_data_types(data: dict[str, Any], type_map: dict[str, str]) -> dict[str, Any]:
    """Cast dict values to specified types. Returns {result: cast_dict}.

    Args:
        data: Input dictionary.
        type_map: Maps field names to type names: ``"int"``, ``"float"``, ``"str"``, ``"bool"``.

    Returns:
        dict with key ``result`` containing the dict with cast values.
    """
    _casters: dict[str, Any] = {"int": int, "float": float, "str": str, "bool": bool}
    result = dict(data)
    for field, type_name in type_map.items():
        if field in result and type_name in _casters:
            result[field] = _casters[type_name](result[field])
    return {"result": result}


@brick(tags=["data", "cleaning", "dict"], category="data_transformation", destructive=False)
def remove_null_values(data: dict[str, Any]) -> dict[str, Any]:
    """Remove keys with None values from a dict. Returns {result: cleaned}.

    Args:
        data: Input dictionary.

    Returns:
        dict with key ``result`` containing only non-None entries.
    """
    return {"result": {k: v for k, v in data.items() if v is not None}}


@brick(tags=["data", "flatten", "dict"], category="data_transformation", destructive=False)
def flatten_nested_dict(data: dict[str, Any], separator: str = ".") -> dict[str, Any]:
    """Flatten a nested dict using dot-separated keys. Returns {result: flat_dict}.

    Args:
        data: Nested dictionary to flatten.
        separator: Key separator (default ``"."``).

    Returns:
        dict with key ``result`` containing the flattened dict.
    """

    def _flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
        out: dict[str, Any] = {}
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_key = f"{prefix}{separator}{k}" if prefix else k
                out.update(_flatten(v, new_key))
        else:
            out[prefix] = obj
        return out

    return {"result": _flatten(data)}


@brick(tags=["data", "dedup", "list"], category="data_transformation", destructive=False)
def deduplicate_dict_list(items: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    """Remove duplicate dicts keeping the first occurrence of each key value. Returns {result: deduped}.

    Args:
        items: List of dicts.
        key: Field to use as the deduplication key.

    Returns:
        dict with key ``result`` containing deduplicated list (first occurrence kept).
    """
    seen: set[Any] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        val = item.get(key)
        if val not in seen:
            seen.add(val)
            result.append(item)
    return {"result": result}


@brick(tags=["data", "sort", "list"], category="data_transformation", destructive=False)
def sort_dict_list(items: list[dict[str, Any]], key: str, reverse: bool = False) -> dict[str, list[dict[str, Any]]]:
    """Sort a list of dicts by a field. Returns {result: sorted_list}.

    Args:
        items: List of dicts to sort.
        key: Field name to sort by.
        reverse: If True, sort in descending order.

    Returns:
        dict with key ``result`` containing the sorted list.
    """
    return {"result": sorted(items, key=lambda x: x.get(key, 0), reverse=reverse)}


@brick(tags=["data", "rename", "dict"], category="data_transformation", destructive=False)
def rename_dict_keys(data: dict[str, Any], rename_map: dict[str, str]) -> dict[str, Any]:
    """Rename dict keys according to a mapping. Returns {result: renamed}.

    Args:
        data: Source dictionary.
        rename_map: Maps old key names to new key names.

    Returns:
        dict with key ``result`` containing the dict with renamed keys.
    """
    result = {}
    for k, v in data.items():
        result[rename_map.get(k, k)] = v
    return {"result": result}


@brick(tags=["data", "group", "list"], category="data_transformation", destructive=False)
def group_by_key(items: list[dict[str, Any]], key: str) -> dict[str, Any]:
    """Group a list of dicts by a field value. Returns {result: grouped_dict}.

    Args:
        items: List of dicts.
        key: Field to group by.

    Returns:
        dict with key ``result`` where each value is a list of matching dicts.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        group_key = str(item.get(key, ""))
        groups.setdefault(group_key, []).append(item)
    return {"result": groups}


@brick(tags=["data", "csv", "export"], category="data_transformation", destructive=False)
def convert_to_csv_str(items: list[dict[str, Any]]) -> dict[str, str]:
    """Convert a list of dicts to a CSV string. Returns {result: csv_string}.

    Args:
        items: List of dicts (must all have the same keys).

    Returns:
        dict with key ``result`` containing the CSV text.
    """
    if not items:
        return {"result": ""}
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(items[0].keys()))
    writer.writeheader()
    writer.writerows(items)
    return {"result": buf.getvalue()}


@brick(tags=["data", "unflatten", "dict"], category="data_transformation", destructive=False)
def unflatten_dict(data: dict[str, Any], separator: str = ".") -> dict[str, Any]:
    """Unflatten a dot-separated flat dict into a nested dict. Returns {result: nested}.

    Args:
        data: Flat dictionary with dot-separated keys.
        separator: Key separator (default ``"."``).

    Returns:
        dict with key ``result`` containing the nested dict.
    """
    result: dict[str, Any] = {}
    for compound_key, value in data.items():
        parts = compound_key.split(separator)
        node = result
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    return {"result": result}


@brick(tags=["data", "aggregate", "math"], category="data_transformation", destructive=False)
def calculate_aggregates(
    items: list[dict[str, Any]],
    field: str,
    operation: Literal["sum", "avg", "min", "max", "count"],
) -> dict[str, float]:
    """Aggregate a numeric field across a list of dicts. Returns {result: aggregated_value}.

    Args:
        items: List of dicts.
        field: Numeric field to aggregate.
        operation: One of ``"sum"``, ``"avg"``, ``"min"``, ``"max"``, ``"count"``.

    Returns:
        dict with key ``result`` containing the aggregated value.

    Raises:
        ValueError: If operation is not recognized.
    """
    values = [float(item[field]) for item in items if field in item]
    if not values:
        return {"result": 0.0}
    ops: dict[str, Any] = {
        "sum": sum,
        "avg": lambda v: sum(v) / len(v),
        "min": min,
        "max": max,
        "count": len,
    }
    if operation not in ops:
        raise ValueError(f"Unknown operation {operation!r}. Use: sum, avg, min, max, count")
    return {"result": float(ops[operation](values))}


@brick(tags=["data", "join", "list"], category="data_transformation", destructive=False)
def join_lists_on_key(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
    key: str,
) -> dict[str, list[dict[str, Any]]]:
    """Inner-join two lists of dicts on a shared key. Returns {result: joined_list}.

    Args:
        left: Left list of dicts.
        right: Right list of dicts.
        key: Field name used as the join key.

    Returns:
        dict with key ``result`` containing merged dicts for matching keys.
    """
    right_index: dict[Any, dict[str, Any]] = {item.get(key): item for item in right}
    result = []
    for item in left:
        match = right_index.get(item.get(key))
        if match:
            result.append({**item, **match})
    return {"result": result}


@brick(tags=["data", "diff", "dict"], category="data_transformation", destructive=False)
def diff_dict_objects(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Compute the diff between two dicts. Returns {result: diff}.

    Args:
        old: Original dictionary.
        new: Updated dictionary.

    Returns:
        dict with key ``result`` containing a dict with ``added``, ``removed``,
        and ``changed`` entries.
    """
    all_keys = set(old) | set(new)
    added = {k: new[k] for k in all_keys if k not in old}
    removed = {k: old[k] for k in all_keys if k not in new}
    changed = {k: {"old": old[k], "new": new[k]} for k in all_keys if k in old and k in new and old[k] != new[k]}
    return {"result": {"added": added, "removed": removed, "changed": changed}}


@brick(tags=["data", "xml", "parsing"], category="data_transformation", destructive=False)
def parse_xml_to_dict(xml_text: str) -> dict[str, Any]:
    """Parse XML text into a nested dict. Returns {result: dict}.

    Args:
        xml_text: Valid XML string.

    Returns:
        dict with key ``result`` containing the parsed XML as a nested dict.
    """

    def _elem_to_dict(elem: ET.Element) -> Any:
        children = list(elem)
        if not children:
            return elem.text or ""
        result: dict[str, Any] = {}
        for child in children:
            val = _elem_to_dict(child)
            if child.tag in result:
                existing = result[child.tag]
                if not isinstance(existing, list):
                    result[child.tag] = [existing]
                result[child.tag].append(val)
            else:
                result[child.tag] = val
        return result

    root = ET.fromstring(xml_text)  # noqa: S314
    return {"result": {root.tag: _elem_to_dict(root)}}


@brick(tags=["data", "security", "masking"], category="data_transformation", destructive=False)
def mask_sensitive_data(data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    """Replace specified field values with '***'. Returns {result: masked_dict}.

    Args:
        data: Input dictionary.
        fields: List of field names to mask.

    Returns:
        dict with key ``result`` containing the dict with sensitive values masked.
    """
    result = dict(data)
    for field in fields:
        if field in result:
            result[field] = "***"
    return {"result": result}


@brick(tags=["data", "pivot", "transform"], category="data_transformation", destructive=False)
def pivot_data_structure(items: list[dict[str, Any]], index_key: str, value_key: str) -> dict[str, Any]:
    """Pivot a list of dicts into {index_value: value}. Returns {result: pivoted}.

    Args:
        items: List of dicts.
        index_key: Field to use as the output key.
        value_key: Field to use as the output value.

    Returns:
        dict with key ``result`` mapping index_key values to value_key values.
    """
    return {"result": {str(item.get(index_key, "")): item.get(value_key) for item in items}}


@brick(tags=["data", "slice", "list"], category="data_transformation", destructive=False)
def slice_dict_list(items: list[dict[str, Any]], start: int, end: int) -> dict[str, list[dict[str, Any]]]:
    """Return a slice of a list of dicts. Returns {result: sliced_list}.

    Args:
        items: Source list.
        start: Start index (inclusive).
        end: End index (exclusive).

    Returns:
        dict with key ``result`` containing the sliced list.
    """
    return {"result": items[start:end]}


@brick(tags=["data", "json", "serialization"], category="data_transformation", destructive=False)
def dict_to_json_str(data: dict[str, Any]) -> dict[str, str]:
    """Serialize a dict to a JSON string. Returns {result: json_string}.

    Args:
        data: Dictionary to serialize.

    Returns:
        dict with key ``result`` containing the JSON string.
    """
    return {"result": json.dumps(data, default=str)}


@brick(tags=["data", "select", "dict"], category="data_transformation", destructive=False)
def select_dict_keys(data: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    """Return a new dict containing only the specified keys. Returns {result: subset}.

    Args:
        data: Source dictionary.
        keys: Keys to include in the output.

    Returns:
        dict with key ``result`` containing only the selected keys.
    """
    return {"result": {k: data[k] for k in keys if k in data}}


@brick(tags=["data", "set", "dict"], category="data_transformation", destructive=False)
def set_dict_field(data: dict[str, Any], field: str, value: Any) -> dict[str, Any]:
    """Set a field in a dict, returning the updated copy. Returns {result: updated_dict}.

    Args:
        data: Source dictionary.
        field: Key to set.
        value: Value to assign.

    Returns:
        dict with key ``result`` containing the updated dict.
    """
    return {"result": {**data, field: value}}


@brick(tags=["data", "count", "list"], category="data_transformation", destructive=False)
def count_dict_list(items: list[dict[str, Any]]) -> dict[str, int]:
    """Return the number of items in a list of dicts. Returns {result: count}.

    Args:
        items: List of dicts.

    Returns:
        dict with key ``result`` containing the count.
    """
    return {"result": len(items)}
