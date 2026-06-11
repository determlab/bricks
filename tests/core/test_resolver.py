"""Tests for bricks.core.resolver."""

from __future__ import annotations

from typing import Any

import pytest

from bricks.core.context import ExecutionContext
from bricks.core.exceptions import VariableResolutionError
from bricks.core.resolver import ReferenceResolver


class TestReferenceResolver:
    def test_resolve_simple_reference(self) -> None:
        ctx = ExecutionContext(inputs={"channel": 3})
        resolver = ReferenceResolver()
        result = resolver.resolve("${inputs.channel}", ctx)
        assert result == 3, f"Expected 3, got {result!r}"

    def test_unresolvable_raises(self) -> None:
        ctx = ExecutionContext()
        resolver = ReferenceResolver()
        with pytest.raises(VariableResolutionError):
            resolver.resolve("${missing.var}", ctx)


class TestResolverEdgeCases:
    def test_plain_string_unchanged(self) -> None:
        ctx = ExecutionContext()
        resolver = ReferenceResolver()
        assert resolver.resolve("hello world", ctx) == "hello world", (
            f"Expected 'hello world', got {resolver.resolve('hello world', ctx)!r}"
        )

    @pytest.mark.parametrize(
        "value,expected",
        [
            (42, 42),
            (3.14, 3.14),
            (True, True),
            (None, None),
        ],
    )
    def test_literal_values_unchanged(self, value: Any, expected: Any) -> None:
        """Non-string literal values are returned unchanged by the resolver."""
        ctx = ExecutionContext()
        resolver = ReferenceResolver()
        result = resolver.resolve(value, ctx)
        assert result == expected, f"Expected {expected!r}, got {result!r}"

    def test_embedded_ref_in_string(self) -> None:
        ctx = ExecutionContext(inputs={"name": "Alice"})
        resolver = ReferenceResolver()
        result = resolver.resolve("Hello, ${inputs.name}!", ctx)
        assert result == "Hello, Alice!", f"Expected 'Hello, Alice!', got {result!r}"

    def test_multiple_refs_in_string(self) -> None:
        ctx = ExecutionContext(inputs={"a": "foo", "b": "bar"})
        resolver = ReferenceResolver()
        result = resolver.resolve("${inputs.a} and ${inputs.b}", ctx)
        assert result == "foo and bar", f"Expected 'foo and bar', got {result!r}"

    def test_nested_dict_resolved(self) -> None:
        ctx = ExecutionContext(inputs={"x": 10})
        resolver = ReferenceResolver()
        result = resolver.resolve({"key": "${inputs.x}", "literal": 5}, ctx)
        assert result == {"key": 10, "literal": 5}, f"Expected {{'key': 10, 'literal': 5}}, got {result!r}"

    def test_list_resolved(self) -> None:
        ctx = ExecutionContext(inputs={"val": 99})
        resolver = ReferenceResolver()
        result = resolver.resolve(["${inputs.val}", 1, 2], ctx)
        assert result == [99, 1, 2], f"Expected [99, 1, 2], got {result!r}"

    def test_unknown_variable_raises(self) -> None:
        ctx = ExecutionContext()
        resolver = ReferenceResolver()
        with pytest.raises(VariableResolutionError):
            resolver.resolve("${unknown_var}", ctx)

    def test_full_match_preserves_type(self) -> None:
        """${var} full match returns the typed value, not a string."""
        ctx = ExecutionContext(inputs={"count": 42})
        resolver = ReferenceResolver()
        result = resolver.resolve("${inputs.count}", ctx)
        assert result == 42, f"Expected 42, got {result!r}"
        assert isinstance(result, int), f"Expected int, got {type(result).__name__}"

    def test_resolve_saved_result(self) -> None:
        ctx = ExecutionContext()
        ctx.save_result("step_output", 3.14)
        resolver = ReferenceResolver()
        result = resolver.resolve("${step_output}", ctx)
        assert result == 3.14, f"Expected 3.14, got {result!r}"

    @pytest.mark.parametrize(
        "value,expected",
        [
            ({}, {}),
            ([], []),
        ],
    )
    def test_resolve_empty_containers(self, value: Any, expected: Any) -> None:
        """Empty dict and list resolve to the same empty container type."""
        ctx = ExecutionContext()
        resolver = ReferenceResolver()
        result = resolver.resolve(value, ctx)
        assert result == expected, f"Expected {expected!r}, got {result!r}"

    def test_nested_list_in_dict(self) -> None:
        ctx = ExecutionContext(inputs={"v": 7})
        resolver = ReferenceResolver()
        result = resolver.resolve({"items": ["${inputs.v}", 2]}, ctx)
        assert result == {"items": [7, 2]}, f"Expected {{'items': [7, 2]}}, got {result!r}"
