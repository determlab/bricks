"""Tests for bricks.core.registry."""

import pytest

from bricks.core.exceptions import BrickNotFoundError, DuplicateBrickError
from bricks.core.models import BrickMeta
from bricks.core.registry import BrickRegistry


class TestRegister:
    def test_register_and_get_roundtrip(self) -> None:
        reg = BrickRegistry()
        meta = BrickMeta(name="test_brick")

        def my_func() -> None:
            pass

        reg.register("test_brick", my_func, meta)
        func, retrieved_meta = reg.get("test_brick")
        assert func is my_func, "Expected the registered function"
        assert retrieved_meta.name == "test_brick", f"Expected 'test_brick', got {retrieved_meta.name!r}"

    def test_duplicate_raises(self) -> None:
        reg = BrickRegistry()
        meta = BrickMeta(name="dup")

        def func() -> None:
            pass

        reg.register("dup", func, meta)
        with pytest.raises(DuplicateBrickError):
            reg.register("dup", func, meta)


class TestGet:
    def test_missing_raises_brick_not_found(self) -> None:
        reg = BrickRegistry()
        with pytest.raises(BrickNotFoundError):
            reg.get("nonexistent")


class TestRegistryListAndHas:
    def test_list_all_sorted(self) -> None:
        reg = BrickRegistry()
        reg.register("zebra", lambda: None, BrickMeta(name="zebra"))
        reg.register("apple", lambda: None, BrickMeta(name="apple"))
        names = [name for name, _ in reg.list_all()]
        assert names == ["apple", "zebra"], f"Expected ['apple', 'zebra'], got {names!r}"

    def test_list_all_empty(self) -> None:
        reg = BrickRegistry()
        assert reg.list_all() == [], f"Expected [], got {reg.list_all()!r}"

    def test_has_returns_false_for_unknown(self) -> None:
        reg = BrickRegistry()
        assert reg.has("nonexistent") is False, f"Expected False, got {reg.has('nonexistent')!r}"

    def test_has_returns_true_after_register(self) -> None:
        reg = BrickRegistry()
        reg.register("my_brick", lambda: None, BrickMeta(name="my_brick"))
        assert reg.has("my_brick") is True, f"Expected True, got {reg.has('my_brick')!r}"

    def test_clear_empties_registry(self) -> None:
        reg = BrickRegistry()
        reg.register("b1", lambda: None, BrickMeta(name="b1"))
        reg.clear()
        assert reg.list_all() == [], f"Expected [], got {reg.list_all()!r}"
        assert reg.has("b1") is False, f"Expected False after clear, got {reg.has('b1')!r}"

    def test_get_raises_for_unknown(self) -> None:
        reg = BrickRegistry()
        with pytest.raises(BrickNotFoundError):
            reg.get("missing")

    def test_multiple_bricks_retrieved_correctly(self) -> None:
        reg = BrickRegistry()

        def fn_a() -> str:
            return "a"

        def fn_b() -> str:
            return "b"

        reg.register("a", fn_a, BrickMeta(name="a"))
        reg.register("b", fn_b, BrickMeta(name="b"))
        callable_a, meta_a = reg.get("a")
        callable_b, meta_b = reg.get("b")
        assert callable_a() == "a", f"Expected 'a', got {callable_a()!r}"
        assert callable_b() == "b", f"Expected 'b', got {callable_b()!r}"
        assert meta_a.name == "a", f"Expected 'a', got {meta_a.name!r}"
        assert meta_b.name == "b", f"Expected 'b', got {meta_b.name!r}"

    def test_list_all_returns_name_meta_tuples(self) -> None:
        reg = BrickRegistry()
        meta = BrickMeta(name="my_brick", tags=["test"])
        reg.register("my_brick", lambda: None, meta)
        result = reg.list_all()
        assert len(result) == 1, f"Expected length 1, got {len(result)}"
        name, retrieved_meta = result[0]
        assert name == "my_brick", f"Expected 'my_brick', got {name!r}"
        assert retrieved_meta.tags == ["test"], f"Expected ['test'], got {retrieved_meta.tags!r}"

    def test_register_many_and_list_all_sorted(self) -> None:
        reg = BrickRegistry()
        names = ["charlie", "alpha", "beta", "delta"]
        for n in names:
            reg.register(n, lambda: None, BrickMeta(name=n))
        listed_names = [name for name, _ in reg.list_all()]
        assert listed_names == sorted(names), f"Expected {sorted(names)!r}, got {listed_names!r}"


class TestFromStdlib:
    def test_from_stdlib_registers_bricks(self) -> None:
        reg = BrickRegistry.from_stdlib()
        all_names = [name for name, _ in reg.list_all()]
        assert len(all_names) > 0, "Expected stdlib bricks to be registered"
        assert "extract_json_from_str" in all_names

    def test_from_stdlib_returns_new_registry_each_call(self) -> None:
        reg1 = BrickRegistry.from_stdlib()
        reg2 = BrickRegistry.from_stdlib()
        assert reg1 is not reg2
