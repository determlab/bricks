"""Tests for bricks.core.catalog.TieredCatalog."""

from __future__ import annotations

import pytest

from bricks.core.brick import brick
from bricks.core.catalog import TieredCatalog
from bricks.core.config import CatalogConfig, ConfigLoader
from bricks.core.exceptions import BrickNotFoundError
from bricks.core.registry import BrickRegistry

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_registry() -> BrickRegistry:
    """Build a registry with a few bricks for testing."""
    reg = BrickRegistry()

    @brick(tags=["math"], description="Add two numbers")
    def add(a: float, b: float) -> float:
        """Add two numbers."""
        return a + b

    @brick(tags=["math", "geometry"], description="Compute circle area")
    def circle_area(radius: float) -> float:
        """Compute circle area."""
        import math

        return math.pi * radius**2

    @brick(tags=["format"], description="Format a display string")
    def format_result(label: str, value: float) -> str:
        """Format a display string."""
        return f"{label}: {value}"

    @brick(tags=["io"], description="Write data to a file")
    def write_file(path: str, content: str) -> None:
        """Write data to a file."""

    for fn in (add, circle_area, format_result, write_file):
        reg.register(fn.__brick_meta__.name, fn, fn.__brick_meta__)

    return reg


# ── list_bricks ───────────────────────────────────────────────────────────────


class TestListBricks:
    def test_empty_common_set_and_empty_cache_returns_empty(self) -> None:
        """list_bricks() returns [] when no common_set and no session cache."""
        catalog = TieredCatalog(registry=_make_registry())
        assert catalog.list_bricks() == [], f"Expected [], got {catalog.list_bricks()!r}"

    def test_common_set_returns_those_bricks(self) -> None:
        """list_bricks() returns schemas for common_set bricks."""
        catalog = TieredCatalog(registry=_make_registry(), common_set=["add", "format_result"])
        result = catalog.list_bricks()
        names = [b["name"] for b in result]
        assert names == ["add", "format_result"], f"Expected ['add', 'format_result'], got {names!r}"

    def test_common_set_unknown_names_silently_skipped(self) -> None:
        """Unknown names in common_set are silently ignored."""
        catalog = TieredCatalog(registry=_make_registry(), common_set=["add", "nonexistent"])
        result = catalog.list_bricks()
        names = [b["name"] for b in result]
        assert names == ["add"], f"Expected ['add'], got {names!r}"

    def test_list_does_not_include_all_bricks(self) -> None:
        """list_bricks() does not dump the entire registry."""
        reg = _make_registry()
        catalog = TieredCatalog(registry=reg, common_set=["add"])
        result = catalog.list_bricks()
        assert len(result) == 1, f"Expected 1 brick, got {len(result)}"

    def test_session_cache_included_after_get_brick(self) -> None:
        """Bricks fetched via get_brick() appear in subsequent list_bricks()."""
        catalog = TieredCatalog(registry=_make_registry())
        catalog.get_brick("circle_area")
        result = catalog.list_bricks()
        names = [b["name"] for b in result]
        assert "circle_area" in names, f"Expected 'circle_area' in {names!r}"

    def test_common_set_and_cache_deduplicated(self) -> None:
        """A brick in both common_set and session cache appears only once."""
        catalog = TieredCatalog(registry=_make_registry(), common_set=["add"])
        catalog.get_brick("add")  # also adds to cache
        result = catalog.list_bricks()
        names = [b["name"] for b in result]
        assert names.count("add") == 1, f"Expected 'add' once, got {names!r}"


# ── lookup_brick ──────────────────────────────────────────────────────────────


class TestLookupBrick:
    def test_lookup_by_name_substring(self) -> None:
        """lookup_brick matches bricks by name substring."""
        catalog = TieredCatalog(registry=_make_registry())
        result = catalog.lookup_brick("add")
        names = [b["name"] for b in result]
        assert "add" in names, f"Expected 'add' in {names!r}"

    def test_lookup_by_tag(self) -> None:
        """lookup_brick matches bricks by tag."""
        catalog = TieredCatalog(registry=_make_registry())
        result = catalog.lookup_brick("math")
        names = [b["name"] for b in result]
        assert "add" in names, f"Expected 'add' in {names!r}"
        assert "circle_area" in names, f"Expected 'circle_area' in {names!r}"

    def test_lookup_by_description_substring(self) -> None:
        """lookup_brick matches bricks by description substring."""
        catalog = TieredCatalog(registry=_make_registry())
        result = catalog.lookup_brick("display string")
        names = [b["name"] for b in result]
        assert "format_result" in names, f"Expected 'format_result' in {names!r}"

    def test_lookup_no_match_returns_empty(self) -> None:
        """lookup_brick returns [] when nothing matches."""
        catalog = TieredCatalog(registry=_make_registry())
        result = catalog.lookup_brick("zzzznonexistent")
        assert result == [], f"Expected [], got {result!r}"

    def test_lookup_adds_to_session_cache(self) -> None:
        """lookup_brick adds matching bricks to the session cache."""
        catalog = TieredCatalog(registry=_make_registry())
        catalog.lookup_brick("math")
        visible = {b["name"] for b in catalog.list_bricks()}
        assert "add" in visible, f"Expected 'add' in session cache: {visible!r}"
        assert "circle_area" in visible, f"Expected 'circle_area' in session cache: {visible!r}"

    def test_lookup_case_insensitive(self) -> None:
        """lookup_brick search is case-insensitive."""
        catalog = TieredCatalog(registry=_make_registry())
        result = catalog.lookup_brick("MATH")
        names = [b["name"] for b in result]
        assert "add" in names, f"Expected 'add' in {names!r}"


# ── get_brick ─────────────────────────────────────────────────────────────────


class TestGetBrick:
    def test_get_brick_returns_schema(self) -> None:
        """get_brick returns a correct schema dict for a known brick."""
        catalog = TieredCatalog(registry=_make_registry())
        schema = catalog.get_brick("add")
        assert schema["name"] == "add", f"Expected 'add', got {schema['name']!r}"
        assert "parameters" in schema, "Expected 'parameters' key in schema"

    def test_get_brick_adds_to_session_cache(self) -> None:
        """get_brick adds the brick to the session cache."""
        catalog = TieredCatalog(registry=_make_registry())
        catalog.get_brick("write_file")
        names = [b["name"] for b in catalog.list_bricks()]
        assert "write_file" in names, f"Expected 'write_file' in session cache: {names!r}"

    def test_get_brick_unknown_raises(self) -> None:
        """get_brick raises BrickNotFoundError for an unknown name."""
        catalog = TieredCatalog(registry=_make_registry())
        with pytest.raises(BrickNotFoundError):
            catalog.get_brick("does_not_exist")


# ── clear_session_cache ───────────────────────────────────────────────────────


class TestClearSessionCache:
    def test_clear_empties_cache(self) -> None:
        """clear_session_cache removes all session-cache bricks from list_bricks."""
        catalog = TieredCatalog(registry=_make_registry())
        catalog.get_brick("add")
        catalog.get_brick("write_file")
        assert len(catalog.list_bricks()) == 2

        catalog.clear_session_cache()
        assert catalog.list_bricks() == [], f"Expected [], got {catalog.list_bricks()!r}"

    def test_clear_does_not_affect_common_set(self) -> None:
        """clear_session_cache does not remove common_set bricks."""
        catalog = TieredCatalog(registry=_make_registry(), common_set=["add"])
        catalog.get_brick("circle_area")
        catalog.clear_session_cache()

        names = [b["name"] for b in catalog.list_bricks()]
        assert "add" in names, f"Expected 'add' still visible: {names!r}"
        assert "circle_area" not in names, f"Expected 'circle_area' gone: {names!r}"


# ── Config integration ────────────────────────────────────────────────────────


class TestCatalogConfig:
    def test_catalog_config_default_is_empty(self) -> None:
        """CatalogConfig defaults to an empty common_set."""
        cfg = CatalogConfig()
        assert cfg.common_set == [], f"Expected [], got {cfg.common_set!r}"

    def test_catalog_config_loaded_from_yaml(self) -> None:
        """CatalogConfig.common_set is populated from bricks.config.yaml."""
        loader = ConfigLoader()
        config = loader.load_string("""
version: "1"
catalog:
  common_set:
    - add
    - format_result
""")
        assert config.catalog.common_set == ["add", "format_result"], (
            f"Expected ['add', 'format_result'], got {config.catalog.common_set!r}"
        )


# ── Enriched list_bricks schema ──────────────────────────────────────────────


class TestEnrichedListBricks:
    def test_list_bricks_includes_category(self) -> None:
        """list_bricks() results include category field."""
        catalog = TieredCatalog(registry=_make_registry(), common_set=["add"])
        result = catalog.list_bricks()
        assert "category" in result[0], f"Expected 'category' in schema keys: {list(result[0].keys())}"

    def test_list_bricks_includes_input_keys(self) -> None:
        """list_bricks() results include input_keys field."""
        catalog = TieredCatalog(registry=_make_registry(), common_set=["add"])
        result = catalog.list_bricks()
        assert "input_keys" in result[0], f"Expected 'input_keys' in schema keys: {list(result[0].keys())}"
        assert result[0]["input_keys"] == ["a", "b"], f"Expected ['a', 'b'], got {result[0]['input_keys']!r}"

    def test_list_bricks_includes_output_keys(self) -> None:
        """list_bricks() results include output_keys field."""
        catalog = TieredCatalog(registry=_make_registry(), common_set=["add"])
        result = catalog.list_bricks()
        assert "output_keys" in result[0], f"Expected 'output_keys' in schema keys: {list(result[0].keys())}"

    def test_category_default_is_general(self) -> None:
        """Bricks without explicit category default to 'general'."""
        catalog = TieredCatalog(registry=_make_registry(), common_set=["add"])
        result = catalog.list_bricks()
        assert result[0]["category"] == "general", f"Expected 'general', got {result[0]['category']!r}"

    def test_custom_category_in_schema(self) -> None:
        """@brick(category='math') is reflected in list_bricks()."""
        reg = BrickRegistry()

        @brick(tags=["math"], category="math")
        def my_add(a: float, b: float) -> dict[str, float]:
            return {"result": a + b}

        reg.register("my_add", my_add, my_add.__brick_meta__)
        catalog = TieredCatalog(registry=reg, common_set=["my_add"])
        result = catalog.list_bricks()
        assert result[0]["category"] == "math", f"Expected 'math', got {result[0]['category']!r}"
