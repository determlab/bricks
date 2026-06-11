"""Tests for ``FilteringSelector`` — wraps another selector and excludes names."""

from __future__ import annotations

from bricks.core.brick import BrickMeta
from bricks.core.filtering_selector import FilteringSelector
from bricks.core.registry import BrickRegistry
from bricks.core.selector import AllBricksSelector


def _registry_with(*names: str) -> BrickRegistry:
    """Build a registry with placeholder bricks for each name."""
    registry = BrickRegistry()

    def _noop() -> dict:  # pragma: no cover - placeholder callable
        return {"result": None}

    for name in names:
        registry.register(name, _noop, BrickMeta(name=name, tags=[], category="test"))
    return registry


class TestFilteringSelector:
    """Verify inner-selector delegation + exclusion semantics."""

    def test_excludes_named_bricks(self) -> None:
        inner = AllBricksSelector()
        registry = _registry_with("filter_dict_list", "map_values", "count_dict_list")

        selector = FilteringSelector(inner=inner, exclude=["filter_dict_list"])
        result = selector.select(task="whatever", registry=registry)

        names = [name for name, _ in result.list_all()]
        assert "filter_dict_list" not in names
        assert "map_values" in names
        assert "count_dict_list" in names

    def test_missing_excluded_name_is_ignored(self) -> None:
        inner = AllBricksSelector()
        registry = _registry_with("a", "b")

        selector = FilteringSelector(inner=inner, exclude=["does_not_exist"])
        result = selector.select(task="", registry=registry)

        assert {n for n, _ in result.list_all()} == {"a", "b"}

    def test_empty_exclusion_returns_inner_unchanged(self) -> None:
        """With no exclusions, FilteringSelector must not rebuild the pool."""
        inner = AllBricksSelector()
        registry = _registry_with("a", "b")

        selector = FilteringSelector(inner=inner, exclude=[])
        result = selector.select(task="", registry=registry)

        # Same object, not a rebuild.
        assert result is registry

    def test_excluded_property_exposes_frozenset(self) -> None:
        selector = FilteringSelector(inner=AllBricksSelector(), exclude=["x", "y"])
        excluded = selector.excluded
        assert excluded == frozenset({"x", "y"})
        assert isinstance(excluded, frozenset)

    def test_inner_selector_runs_before_filter(self) -> None:
        """FilteringSelector must not bypass its inner selector — it
        post-filters whatever inner returns."""

        calls: list[str] = []

        class RecordingSelector(AllBricksSelector):
            def select(self, task, registry):  # type: ignore[override]
                calls.append(task)
                return super().select(task, registry)

        selector = FilteringSelector(inner=RecordingSelector(), exclude=["x"])
        selector.select(task="hello", registry=_registry_with("x", "y"))
        assert calls == ["hello"]
