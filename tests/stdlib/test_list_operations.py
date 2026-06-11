"""Tests for bricks/stdlib/list_operations.py — 10 tests."""

from __future__ import annotations

import pytest

from bricks.stdlib.list_operations import (
    chunk_list,
    difference_lists,
    flatten_list,
    intersect_lists,
    is_empty_list,
    map_values,
    reduce_sum,
    reverse_list,
    take_first_n,
    unique_values,
    zip_lists,
)


def test_unique_values_preserves_order() -> None:
    assert unique_values([3, 1, 2, 1, 3])["result"] == [3, 1, 2]


def test_flatten_list_one_level() -> None:
    assert flatten_list([[1, 2], [3, 4]])["result"] == [1, 2, 3, 4]


def test_chunk_list_splits_evenly() -> None:
    assert chunk_list([1, 2, 3, 4], 2)["result"] == [[1, 2], [3, 4]]


def test_chunk_list_size_zero_raises() -> None:
    with pytest.raises(ValueError):
        chunk_list([1, 2], 0)


def test_zip_lists_pairs_elements() -> None:
    assert zip_lists([1, 2], ["a", "b"])["result"] == [[1, "a"], [2, "b"]]


def test_intersect_lists_common_elements() -> None:
    assert intersect_lists([1, 2, 3], [2, 3, 4])["result"] == [2, 3]


def test_difference_lists_excludes_b() -> None:
    assert difference_lists([1, 2, 3], [2])["result"] == [1, 3]


def test_reverse_list_reverses() -> None:
    assert reverse_list([1, 2, 3])["result"] == [3, 2, 1]


def test_take_first_n_returns_head() -> None:
    assert take_first_n([10, 20, 30, 40], 2)["result"] == [10, 20]


def test_map_values_extracts_field() -> None:
    items = [{"name": "Alice"}, {"name": "Bob"}]
    assert map_values(items, "name")["result"] == ["Alice", "Bob"]


def test_reduce_sum_totals_values() -> None:
    assert reduce_sum([1.0, 2.0, 3.0])["result"] == pytest.approx(6.0)


def test_is_empty_list_returns_true_for_empty() -> None:
    assert is_empty_list([])["result"] is True


def test_is_empty_list_returns_false_for_nonempty() -> None:
    assert is_empty_list([1, 2, 3])["result"] is False
