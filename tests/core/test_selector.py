"""Tests for bricks.core.selector."""

from __future__ import annotations

from bricks.core.brick import brick
from bricks.core.registry import BrickRegistry
from bricks.core.selector import AllBricksSelector


class TestAllBricksSelector:
    """Tests for AllBricksSelector."""

    def test_returns_full_registry(self) -> None:
        """AllBricksSelector.select() returns the same registry."""
        reg = BrickRegistry()

        @brick(description="Add a + b. Returns {result: a+b}.")
        def add(a: float, b: float) -> dict[str, float]:
            return {"result": a + b}

        reg.register("add", add, add.__brick_meta__)

        selector = AllBricksSelector()
        result = selector.select("some task", reg)
        assert result is reg

    def test_preserves_all_bricks(self) -> None:
        """AllBricksSelector preserves all bricks in the registry."""
        reg = BrickRegistry()

        @brick(description="Add a + b. Returns {result: a+b}.")
        def add(a: float, b: float) -> dict[str, float]:
            return {"result": a + b}

        @brick(description="Multiply a * b. Returns {result: a*b}.")
        def multiply(a: float, b: float) -> dict[str, float]:
            return {"result": a * b}

        reg.register("add", add, add.__brick_meta__)
        reg.register("multiply", multiply, multiply.__brick_meta__)

        selector = AllBricksSelector()
        result = selector.select("calculate something", reg)
        names = [name for name, _ in result.list_all()]
        assert "add" in names
        assert "multiply" in names
        assert len(names) == 2

    def test_empty_registry(self) -> None:
        """AllBricksSelector works with an empty registry."""
        reg = BrickRegistry()
        selector = AllBricksSelector()
        result = selector.select("any task", reg)
        assert list(result.list_all()) == []
