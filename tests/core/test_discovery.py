"""Tests for bricks.core.discovery."""

from __future__ import annotations

import textwrap
import types
from pathlib import Path
from typing import Any, ClassVar

import pytest

from bricks.core.brick import BaseBrick, BrickModel, brick
from bricks.core.discovery import BrickDiscovery
from bricks.core.models import BrickMeta
from bricks.core.registry import BrickRegistry


class TestDiscoverModule:
    def test_discovers_decorated_function(self) -> None:
        """A function with @brick should be auto-registered."""
        mod = types.ModuleType("fake_mod")

        @brick(tags=["test"], description="A test brick")
        def my_test_brick(x: int) -> int:
            return x

        mod.my_test_brick = my_test_brick  # type: ignore[attr-defined]

        reg = BrickRegistry()
        disc = BrickDiscovery(registry=reg)
        found = disc.discover_module(mod)

        assert "my_test_brick" in found, "Expected 'my_test_brick' to be in collection"
        assert reg.has("my_test_brick"), "Expected 'my_test_brick' to be registered"

    def test_discovers_class_based_brick(self) -> None:
        """A BaseBrick subclass should be auto-registered."""
        mod = types.ModuleType("fake_mod2")

        class MyClassBrick(BaseBrick):
            class Meta:
                name = "my_class_brick"
                tags: ClassVar[list[str]] = ["test"]
                destructive = False

            class Input(BrickModel):
                x: int

            class Output(BrickModel):
                result: int

            def execute(self, inputs: BrickModel, metadata: BrickMeta) -> dict[str, Any]:
                return {"result": 42}

        mod.MyClassBrick = MyClassBrick  # type: ignore[attr-defined]

        reg = BrickRegistry()
        disc = BrickDiscovery(registry=reg)
        found = disc.discover_module(mod)

        assert "my_class_brick" in found, "Expected 'my_class_brick' to be in collection"
        assert reg.has("my_class_brick"), "Expected 'my_class_brick' to be registered"

    def test_skips_duplicate_names(self) -> None:
        """Already-registered names should not be re-registered."""
        mod = types.ModuleType("fake_mod3")

        @brick(description="First")
        def dupe_brick(x: int) -> int:
            return x

        mod.dupe_brick = dupe_brick  # type: ignore[attr-defined]

        reg = BrickRegistry()
        reg.register("dupe_brick", lambda: None, BrickMeta(name="dupe_brick"))
        disc = BrickDiscovery(registry=reg)
        found = disc.discover_module(mod)

        # skipped because already registered
        assert "dupe_brick" not in found, "Expected 'dupe_brick' not to be in collection"

    def test_ignores_non_brick_objects(self) -> None:
        """Plain functions and classes without brick markers are ignored."""
        mod = types.ModuleType("fake_mod4")

        def plain_function(x: int) -> int:
            return x

        mod.plain_function = plain_function  # type: ignore[attr-defined]
        mod.some_int = 42  # type: ignore[attr-defined]

        reg = BrickRegistry()
        disc = BrickDiscovery(registry=reg)
        found = disc.discover_module(mod)

        assert found == [], f"Expected [], got {found!r}"
        assert not reg.has("plain_function"), "Expected 'plain_function' not to be registered"


class TestDiscoverPath:
    def test_discovers_bricks_from_file(self, tmp_path: Path) -> None:
        """Bricks defined in a .py file should be discovered."""
        brick_file = tmp_path / "my_bricks.py"
        brick_file.write_text(
            textwrap.dedent("""
                from bricks.core.brick import brick

                @brick(tags=["math"], description="Adds two numbers")
                def add_numbers(a: int, b: int) -> int:
                    return a + b
            """).strip()
        )

        reg = BrickRegistry()
        disc = BrickDiscovery(registry=reg)
        found = disc.discover_path(brick_file)

        assert "add_numbers" in found, "Expected 'add_numbers' to be in collection"
        assert reg.has("add_numbers"), "Expected 'add_numbers' to be registered"

    def test_raises_for_missing_file(self, tmp_path: Path) -> None:
        """FileNotFoundError raised when path does not exist."""
        reg = BrickRegistry()
        disc = BrickDiscovery(registry=reg)
        with pytest.raises(FileNotFoundError):
            disc.discover_path(tmp_path / "nonexistent.py")


class TestDiscoverPackage:
    def test_discovers_bricks_from_directory(self, tmp_path: Path) -> None:
        """All non-underscore .py files in a dir should be scanned."""
        (tmp_path / "bricks_a.py").write_text(
            textwrap.dedent("""
                from bricks.core.brick import brick

                @brick(description="Brick A")
                def brick_alpha(x: int) -> int:
                    return x
            """).strip()
        )
        (tmp_path / "bricks_b.py").write_text(
            textwrap.dedent("""
                from bricks.core.brick import brick

                @brick(description="Brick B")
                def brick_beta(x: int) -> int:
                    return x
            """).strip()
        )
        (tmp_path / "_private.py").write_text(
            textwrap.dedent("""
                from bricks.core.brick import brick

                @brick(description="Private - should be skipped")
                def private_brick(x: int) -> int:
                    return x
            """).strip()
        )

        reg = BrickRegistry()
        disc = BrickDiscovery(registry=reg)
        found = disc.discover_package(tmp_path)

        assert "brick_alpha" in found, "Expected 'brick_alpha' to be in collection"
        assert "brick_beta" in found, "Expected 'brick_beta' to be in collection"
        # skipped (underscore prefix)
        assert "private_brick" not in found, "Expected 'private_brick' not to be in collection"

    def test_raises_for_non_directory(self, tmp_path: Path) -> None:
        """NotADirectoryError raised when path is a file, not a directory."""
        py_file = tmp_path / "file.py"
        py_file.write_text("x = 1")
        reg = BrickRegistry()
        disc = BrickDiscovery(registry=reg)
        with pytest.raises(NotADirectoryError):
            disc.discover_package(py_file)
