"""List Operations bricks — 10 bricks."""

from __future__ import annotations

from typing import Any

from bricks.core.brick import brick


@brick(tags=["list", "dedup", "unique"], category="list_operations", destructive=False)
def unique_values(items: list[Any]) -> dict[str, list[Any]]:
    """Return unique values from a list, preserving order. Returns {result: unique_list}.

    Args:
        items: List potentially containing duplicates.

    Returns:
        dict with key ``result`` containing deduplicated list (first occurrence kept).
    """
    seen: set[Any] = set()
    result = []
    for item in items:
        key = str(item)  # hashable representation
        if key not in seen:
            seen.add(key)
            result.append(item)
    return {"result": result}


@brick(tags=["list", "flatten"], category="list_operations", destructive=False)
def flatten_list(nested: list[list[Any]]) -> dict[str, list[Any]]:
    """Flatten one level of nesting from a list of lists. Returns {result: flat_list}.

    Args:
        nested: List of lists.

    Returns:
        dict with key ``result`` containing the flattened list.
    """
    return {"result": [item for sublist in nested for item in sublist]}


@brick(tags=["list", "chunk", "split"], category="list_operations", destructive=False)
def chunk_list(items: list[Any], size: int) -> dict[str, list[list[Any]]]:
    """Split a list into chunks of a given size. Returns {result: chunks}.

    Args:
        items: Input list.
        size: Chunk size (must be >= 1).

    Returns:
        dict with key ``result`` containing the list of chunks.

    Raises:
        ValueError: If size < 1.
    """
    if size < 1:
        raise ValueError("size must be >= 1")
    return {"result": [items[i : i + size] for i in range(0, len(items), size)]}


@brick(tags=["list", "zip", "combine"], category="list_operations", destructive=False)
def zip_lists(a: list[Any], b: list[Any]) -> dict[str, list[list[Any]]]:
    """Zip two lists into a list of [a_val, b_val] pairs. Returns {result: pairs}.

    Args:
        a: First list.
        b: Second list.

    Returns:
        dict with key ``result`` containing paired elements (stops at shorter list).
    """
    return {"result": [[x, y] for x, y in zip(a, b, strict=False)]}


@brick(tags=["list", "set", "intersection"], category="list_operations", destructive=False)
def intersect_lists(a: list[Any], b: list[Any]) -> dict[str, list[Any]]:
    """Return elements present in both lists (set intersection). Returns {result: common}.

    Args:
        a: First list.
        b: Second list.

    Returns:
        dict with key ``result`` containing elements in both lists (order from a).
    """
    b_set = {str(x) for x in b}
    return {"result": [x for x in a if str(x) in b_set]}


@brick(tags=["list", "set", "difference"], category="list_operations", destructive=False)
def difference_lists(a: list[Any], b: list[Any]) -> dict[str, list[Any]]:
    """Return elements in a but not in b (set difference). Returns {result: diff}.

    Args:
        a: Source list.
        b: List of items to exclude.

    Returns:
        dict with key ``result`` containing elements in a that are not in b.
    """
    b_set = {str(x) for x in b}
    return {"result": [x for x in a if str(x) not in b_set]}


@brick(tags=["list", "reverse"], category="list_operations", destructive=False)
def reverse_list(items: list[Any]) -> dict[str, list[Any]]:
    """Return a reversed copy of a list. Returns {result: reversed_list}.

    Args:
        items: Input list.

    Returns:
        dict with key ``result`` containing the list in reverse order.
    """
    return {"result": list(reversed(items))}


@brick(tags=["list", "slice", "head"], category="list_operations", destructive=False)
def take_first_n(items: list[Any], n: int) -> dict[str, list[Any]]:
    """Return the first n elements of a list. Returns {result: head}.

    Args:
        items: Input list.
        n: Number of elements to take.

    Returns:
        dict with key ``result`` containing the first n items.
    """
    return {"result": items[:n]}


@brick(tags=["list", "map", "extraction"], category="list_operations", destructive=False)
def map_values(items: list[dict[str, Any]], key: str) -> dict[str, list[Any]]:
    """Extract a field from each dict in a list. Returns {result: values}.

    Args:
        items: List of dicts.
        key: Field name to extract from each dict.

    Returns:
        dict with key ``result`` containing the extracted values.
    """
    return {"result": [item.get(key) for item in items]}


@brick(tags=["list", "reduce", "sum", "math"], category="list_operations", destructive=False)
def reduce_sum(values: list[float]) -> dict[str, float]:
    """Sum all numeric values in a list. Returns {result: total}.

    Args:
        values: List of floats.

    Returns:
        dict with key ``result`` containing the sum.
    """
    return {"result": sum(values)}


@brick(tags=["list", "check"], category="list", destructive=False)
def is_empty_list(items: list[object]) -> dict[str, bool]:
    """Check whether a list is empty. Returns {result: bool}.

    Args:
        items: List to check.

    Returns:
        dict with key ``result`` containing ``True`` if the list is empty.
    """
    return {"result": len(items) == 0}
