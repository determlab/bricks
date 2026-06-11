"""Tests for bricks.core.brick."""

from __future__ import annotations

from typing import Any, cast

import pytest

from bricks.core.brick import BaseBrick, BrickFunction, BrickModel, brick
from bricks.core.models import BrickMeta


class TestBrickDecorator:
    def test_decorator_attaches_meta(self) -> None:
        @brick(tags=["test"], description="A test brick")
        def my_brick(x: int) -> int:
            return x

        assert hasattr(my_brick, "__brick_meta__"), "Expected __brick_meta__ attribute"
        meta_name = cast(BrickFunction, my_brick).__brick_meta__.name
        assert meta_name == "my_brick", f"Expected 'my_brick', got {meta_name!r}"

    def test_decorator_returns_unwrapped_function(self) -> None:
        @brick()
        def identity(x: int) -> int:
            return x

        assert identity(42) == 42, f"Expected 42, got {identity(42)!r}"

    def test_decorator_preserves_callable(self) -> None:
        @brick()
        def double(x: int) -> int:
            return x * 2

        assert double(5) == 10, f"Expected 10, got {double(5)!r}"

    def test_decorator_with_all_kwargs(self) -> None:
        @brick(tags=["hw"], destructive=True, idempotent=False, description="A test")
        def my_func(x: int) -> int:
            return x

        meta = cast(BrickFunction, my_func).__brick_meta__
        assert meta.tags == ["hw"], f"Expected ['hw'], got {meta.tags!r}"
        assert meta.destructive is True, f"Expected True, got {meta.destructive!r}"
        assert meta.idempotent is False, f"Expected False, got {meta.idempotent!r}"
        assert meta.description == "A test", f"Expected 'A test', got {meta.description!r}"

    def test_decorator_defaults(self) -> None:
        @brick()
        def my_func() -> None:
            pass

        meta = cast(BrickFunction, my_func).__brick_meta__
        assert meta.tags == [], f"Expected [], got {meta.tags!r}"
        assert meta.destructive is False, f"Expected False, got {meta.destructive!r}"
        assert meta.idempotent is True, f"Expected True, got {meta.idempotent!r}"

    def test_decorator_uses_docstring_as_description(self) -> None:
        @brick()
        def my_func() -> None:
            """This is the docstring."""

        meta = cast(BrickFunction, my_func).__brick_meta__
        assert "docstring" in meta.description, f"Expected 'docstring' in {meta.description!r}"

    def test_decorator_name_matches_function(self) -> None:
        @brick()
        def compute_value(x: int) -> int:
            return x

        assert cast(BrickFunction, compute_value).__brick_meta__.name == "compute_value", "Expected 'compute_value'"

    def test_decorator_empty_description_falls_back_to_docstring(self) -> None:
        @brick(description="")
        def my_func() -> None:
            """Fallback doc."""

        meta = cast(BrickFunction, my_func).__brick_meta__
        assert "Fallback doc" in meta.description, f"Expected 'Fallback doc' in {meta.description!r}"

    def test_decorator_explicit_description_overrides_docstring(self) -> None:
        @brick(description="Explicit desc")
        def my_func() -> None:
            """Docstring."""

        meta = cast(BrickFunction, my_func).__brick_meta__
        assert meta.description == "Explicit desc", f"Expected 'Explicit desc', got {meta.description!r}"

    def test_decorator_multiple_tags(self) -> None:
        @brick(tags=["tag1", "tag2", "tag3"])
        def my_func() -> None:
            pass

        meta = cast(BrickFunction, my_func).__brick_meta__
        assert meta.tags == ["tag1", "tag2", "tag3"], f"Expected ['tag1', 'tag2', 'tag3'], got {meta.tags!r}"

    def test_decorator_category_default(self) -> None:
        @brick()
        def my_func() -> None:
            pass

        meta = cast(BrickFunction, my_func).__brick_meta__
        assert meta.category == "general", f"Expected 'general', got {meta.category!r}"

    def test_decorator_category_custom(self) -> None:
        @brick(category="math")
        def my_func(a: float, b: float) -> dict[str, float]:
            return {"result": a + b}

        meta = cast(BrickFunction, my_func).__brick_meta__
        assert meta.category == "math", f"Expected 'math', got {meta.category!r}"


class TestBrickModel:
    def test_subclass_validates(self) -> None:
        class MyInput(BrickModel):
            channel: int

        inp = MyInput(channel=3)
        assert inp.channel == 3, f"Expected 3, got {inp.channel!r}"

    def test_brick_model_is_pydantic(self) -> None:
        from pydantic import BaseModel

        assert issubclass(BrickModel, BaseModel), "Expected BrickModel to be a subclass of BaseModel"

    def test_brick_model_subclass_validates_with_defaults(self) -> None:
        class MyInput(BrickModel):
            x: int
            y: float = 1.0

        inp = MyInput(x=5)
        assert inp.x == 5, f"Expected 5, got {inp.x!r}"
        assert inp.y == 1.0, f"Expected 1.0, got {inp.y!r}"

    def test_brick_model_rejects_wrong_type(self) -> None:
        from pydantic import ValidationError

        class MyInput(BrickModel):
            x: int

        with pytest.raises(ValidationError):
            MyInput(x="not_an_int")  # type: ignore[arg-type]


class TestBaseBrick:
    def test_cannot_instantiate_abstract(self) -> None:
        with pytest.raises(TypeError):
            BaseBrick()  # type: ignore[abstract]

    def test_concrete_subclass_can_instantiate(self) -> None:
        class ConcreteBrick(BaseBrick):
            def execute(self, inputs: BrickModel, metadata: BrickMeta) -> dict[str, Any]:
                return {}

        b = ConcreteBrick()
        assert b is not None, "Expected non-None value"

    def test_default_meta_values(self) -> None:
        assert BaseBrick.Meta.destructive is False, f"Expected False, got {BaseBrick.Meta.destructive!r}"
        assert BaseBrick.Meta.idempotent is True, f"Expected True, got {BaseBrick.Meta.idempotent!r}"

    def test_concrete_subclass_execute_called(self) -> None:
        class AddBrick(BaseBrick):
            def execute(self, inputs: BrickModel, metadata: BrickMeta) -> dict[str, Any]:
                return {"result": 42}

        b = AddBrick()
        meta = BrickMeta(name="add")
        result = b.execute(BrickModel(), meta)
        assert result == {"result": 42}, f"Expected {{'result': 42}}, got {result!r}"

    def test_base_brick_meta_has_tags(self) -> None:
        assert hasattr(BaseBrick.Meta, "tags"), "Expected 'tags' attribute on BaseBrick.Meta"
        assert BaseBrick.Meta.tags == [], f"Expected [], got {BaseBrick.Meta.tags!r}"

    def test_base_brick_has_input_output(self) -> None:
        assert issubclass(BaseBrick.Input, BrickModel), "Expected BaseBrick.Input to be a subclass of BrickModel"
        assert issubclass(BaseBrick.Output, BrickModel), "Expected BaseBrick.Output to be a subclass of BrickModel"
