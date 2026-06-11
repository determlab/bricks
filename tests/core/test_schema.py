"""Tests for bricks.core.schema."""

from __future__ import annotations

import pytest

from bricks.core.brick import brick
from bricks.core.exceptions import BrickNotFoundError
from bricks.core.models import BlueprintDefinition, StepDefinition
from bricks.core.registry import BrickRegistry
from bricks.core.schema import blueprint_schema, brick_schema, compact_brick_signatures, registry_schema


def _make_reg() -> BrickRegistry:
    """Create a registry with an 'add' brick for testing."""
    reg = BrickRegistry()

    @brick(tags=["math"], description="Add two numbers", destructive=False)
    def add(a: int, b: int) -> int:
        return a + b

    reg.register("add", add, add.__brick_meta__)
    return reg


class TestBrickSchema:
    def test_schema_has_expected_keys(self) -> None:
        """brick_schema returns correct metadata fields."""
        reg = _make_reg()
        schema = brick_schema("add", reg)
        assert schema["name"] == "add", f"Expected 'add', got {schema['name']!r}"
        assert schema["description"] == "Add two numbers", f"Expected 'Add two numbers', got {schema['description']!r}"
        assert schema["tags"] == ["math"], f"Expected ['math'], got {schema['tags']!r}"
        assert schema["destructive"] is False, f"Expected False, got {schema['destructive']!r}"
        assert "parameters" in schema, "Expected 'parameters' key in schema"

    def test_schema_parameters_have_correct_structure(self) -> None:
        """Parameters dict includes correct type and required info."""
        reg = _make_reg()
        schema = brick_schema("add", reg)
        params = schema["parameters"]
        assert "a" in params, "Expected 'a' in parameters"
        assert "b" in params, "Expected 'b' in parameters"
        assert params["a"]["required"] is True, "Expected parameter 'a' to be required"

    def test_schema_raises_for_unknown_brick(self) -> None:
        """BrickNotFoundError raised when brick is not registered."""
        reg = BrickRegistry()
        with pytest.raises(BrickNotFoundError):
            brick_schema("nonexistent", reg)

    def test_schema_idempotent_field(self) -> None:
        """brick_schema includes idempotent field from metadata."""
        reg = _make_reg()
        schema = brick_schema("add", reg)
        assert "idempotent" in schema, "Expected 'idempotent' key in schema"

    def test_schema_parameter_type_annotation(self) -> None:
        """Parameter type annotation is captured as a string."""
        reg = _make_reg()
        schema = brick_schema("add", reg)
        params = schema["parameters"]
        # int annotation should be present as a string form
        assert "int" in params["a"]["type"], f"Expected 'int' in type annotation, got {params['a']['type']!r}"


class TestRegistrySchema:
    def test_registry_schema_returns_list(self) -> None:
        """registry_schema returns a list with one entry per brick."""
        reg = _make_reg()
        schemas = registry_schema(reg)
        assert isinstance(schemas, list), f"Expected list, got {type(schemas).__name__}"
        assert len(schemas) == 1, f"Expected length 1, got {len(schemas)}"
        assert schemas[0]["name"] == "add", f"Expected 'add', got {schemas[0]['name']!r}"

    def test_empty_registry_returns_empty_list(self) -> None:
        """registry_schema returns empty list for empty registry."""
        reg = BrickRegistry()
        assert registry_schema(reg) == [], f"Expected [], got {registry_schema(reg)!r}"

    def test_registry_schema_sorted_by_name(self) -> None:
        """registry_schema results are sorted alphabetically by brick name."""
        reg = BrickRegistry()

        @brick(description="Zebra")
        def zebra_brick(x: int) -> int:
            return x

        @brick(description="Alpha")
        def alpha_brick(x: int) -> int:
            return x

        reg.register("zebra_brick", zebra_brick, zebra_brick.__brick_meta__)
        reg.register("alpha_brick", alpha_brick, alpha_brick.__brick_meta__)

        schemas = registry_schema(reg)
        assert schemas[0]["name"] == "alpha_brick", f"Expected 'alpha_brick' first, got {schemas[0]['name']!r}"
        assert schemas[1]["name"] == "zebra_brick", f"Expected 'zebra_brick' second, got {schemas[1]['name']!r}"


class TestBlueprintSchema:
    def test_blueprint_schema_has_expected_keys(self) -> None:
        """blueprint_schema returns correct top-level keys."""
        bp = BlueprintDefinition(
            name="my_bp",
            description="A test blueprint",
            inputs={"x": "int"},
            steps=[
                StepDefinition(
                    name="s1",
                    brick="add",
                    params={"a": "${inputs.x}", "b": 1},
                )
            ],
            outputs_map={"result": "${s1}"},
        )
        schema = blueprint_schema(bp)
        assert schema["name"] == "my_bp", f"Expected 'my_bp', got {schema['name']!r}"
        assert schema["description"] == "A test blueprint", (
            f"Expected 'A test blueprint', got {schema['description']!r}"
        )
        assert schema["inputs"] == {"x": "int"}, f"Expected {{'x': 'int'}}, got {schema['inputs']!r}"
        assert len(schema["steps"]) == 1, f"Expected length 1, got {len(schema['steps'])}"
        assert schema["steps"][0]["name"] == "s1", f"Expected 's1', got {schema['steps'][0]['name']!r}"
        assert schema["outputs_map"] == {"result": "${s1}"}, "Expected outputs_map mismatch"

    def test_blueprint_schema_step_fields(self) -> None:
        """blueprint_schema step entries include all required step fields."""
        bp = BlueprintDefinition(
            name="test_bp",
            steps=[
                StepDefinition(
                    name="step1",
                    brick="some_brick",
                    params={"key": "value"},
                    save_as="step1_result",
                )
            ],
        )
        schema = blueprint_schema(bp)
        step = schema["steps"][0]
        assert step["name"] == "step1", f"Expected 'step1', got {step['name']!r}"
        assert step["brick"] == "some_brick", f"Expected 'some_brick', got {step['brick']!r}"
        assert step["params"] == {"key": "value"}, "Expected params mismatch"
        assert step["save_as"] == "step1_result", f"Expected 'step1_result', got {step['save_as']!r}"

    def test_blueprint_schema_empty_blueprint(self) -> None:
        """blueprint_schema works with a blueprint that has no steps."""
        bp = BlueprintDefinition(name="empty_bp")
        schema = blueprint_schema(bp)
        assert schema["name"] == "empty_bp", f"Expected 'empty_bp', got {schema['name']!r}"
        assert schema["steps"] == [], f"Expected [], got {schema['steps']!r}"
        assert schema["inputs"] == {}, f"Expected {{}}, got {schema['inputs']!r}"
        assert schema["outputs_map"] == {}, f"Expected {{}}, got {schema['outputs_map']!r}"


class TestCompactBrickSignatures:
    """Tests for compact_brick_signatures()."""

    def test_one_liner_format(self) -> None:
        """Each brick gets a single line with name(params) → output."""
        reg = BrickRegistry()

        @brick(tags=["math"], description="Multiply two numbers")
        def multiply(a: float, b: float) -> dict[str, float]:
            return {"result": a * b}

        reg.register("multiply", multiply, multiply.__brick_meta__)
        result = compact_brick_signatures(reg)
        assert "multiply(a: float, b: float)" in result
        assert "→" in result

    def test_default_values_shown(self) -> None:
        """Bricks with default params show =default."""
        reg = BrickRegistry()

        @brick(description="Round a value")
        def round_value(value: float, decimals: int = 2) -> dict[str, float]:
            return {"result": round(value, decimals)}

        reg.register("round_value", round_value, round_value.__brick_meta__)
        result = compact_brick_signatures(reg)
        assert "decimals: int=2" in result

    def test_sorted_alphabetically(self) -> None:
        """Signatures are sorted alphabetically by brick name."""
        reg = BrickRegistry()

        @brick(description="Zebra")
        def zebra(x: float) -> dict[str, float]:
            return {"result": x}

        @brick(description="Alpha")
        def alpha(x: float) -> dict[str, float]:
            return {"result": x}

        reg.register("zebra", zebra, zebra.__brick_meta__)
        reg.register("alpha", alpha, alpha.__brick_meta__)
        result = compact_brick_signatures(reg)
        lines = result.strip().split("\n")
        assert lines[0].startswith("alpha(")
        assert lines[1].startswith("zebra(")

    def test_empty_registry(self) -> None:
        """Empty registry returns empty string."""
        reg = BrickRegistry()
        assert compact_brick_signatures(reg) == ""

    def test_compact_signatures_sort_alphabetically(self) -> None:
        """``compact_brick_signatures`` emits one line per brick, sorted by name."""
        reg = BrickRegistry()

        @brick(description="Returns {result: a+b}.")
        def add(a: float, b: float) -> dict[str, float]:
            return {"result": a + b}

        @brick(description="Returns {display: str}.")
        def format_result(label: str, value: float) -> dict[str, str]:
            return {"display": f"{label}: {value}"}

        @brick(description="Returns {result: a*b}.")
        def multiply(a: float, b: float) -> dict[str, float]:
            return {"result": a * b}

        @brick(description="Returns {result: rounded float}.")
        def round_value(value: float, ndigits: int) -> dict[str, float]:
            return {"result": round(value, ndigits)}

        @brick(description="Returns {result: a-b}.")
        def subtract(a: float, b: float) -> dict[str, float]:
            return {"result": a - b}

        for fn in (multiply, round_value, add, subtract, format_result):
            reg.register(fn.__name__, fn, fn.__brick_meta__)

        result = compact_brick_signatures(reg)
        lines = result.strip().split("\n")
        assert len(lines) == 5
        # Should be sorted: add, format_result, multiply, round_value, subtract
        assert lines[0].startswith("add(")
        assert lines[1].startswith("format_result(")
        assert lines[2].startswith("multiply(")
        assert lines[3].startswith("round_value(")
        assert lines[4].startswith("subtract(")


class TestOutputKeyTable:
    """Tests for output_key_table()."""

    def test_table_format(self) -> None:
        """Table includes all bricks with arrow-separated name → keys."""
        from bricks.core.schema import output_key_table

        reg = BrickRegistry()

        @brick(description="Add a + b. Returns {result: a+b}.")
        def add(a: float, b: float) -> dict[str, float]:
            return {"result": a + b}

        @brick(description="Format display. Returns {display: str}.")
        def fmt(label: str, value: float) -> dict[str, str]:
            return {"display": f"{label}: {value}"}

        reg.register("add", add, add.__brick_meta__)
        reg.register("fmt", fmt, fmt.__brick_meta__)

        result = output_key_table(reg)
        assert "Output keys" in result
        assert "add" in result
        assert "→ result" in result
        assert "fmt" in result
        assert "→ display" in result

    def test_table_alignment(self) -> None:
        """Names are padded to the same width for readability."""
        from bricks.core.schema import output_key_table

        reg = BrickRegistry()

        @brick(description="Returns {result: float}.")
        def short(x: float) -> dict[str, float]:
            return {"result": x}

        @brick(description="Returns {value: float}.")
        def much_longer_name(x: float) -> dict[str, float]:
            return {"value": x}

        reg.register("short", short, short.__brick_meta__)
        reg.register("much_longer_name", much_longer_name, much_longer_name.__brick_meta__)

        result = output_key_table(reg)
        lines = [ln for ln in result.split("\n") if "→" in ln]
        # Both arrow positions should align
        arrow_positions = [ln.index("→") for ln in lines]
        assert len(set(arrow_positions)) == 1, f"Arrows not aligned: positions {arrow_positions}"

    def test_output_key_table_with_multiple_bricks(self) -> None:
        """``output_key_table`` lists each brick with its arrow-separated keys."""
        from bricks.core.schema import output_key_table

        reg = BrickRegistry()

        @brick(description="Returns {result: a*b}.")
        def multiply(a: float, b: float) -> dict[str, float]:
            return {"result": a * b}

        @brick(description="Returns {result: rounded float}.")
        def round_value(value: float, ndigits: int) -> dict[str, float]:
            return {"result": round(value, ndigits)}

        @brick(description="Returns {result: a+b}.")
        def add(a: float, b: float) -> dict[str, float]:
            return {"result": a + b}

        @brick(description="Returns {display: str}.")
        def format_result(label: str, value: float) -> dict[str, str]:
            return {"display": f"{label}: {value}"}

        for fn in (multiply, round_value, add, format_result):
            reg.register(fn.__name__, fn, fn.__brick_meta__)

        result = output_key_table(reg)
        assert "multiply" in result
        assert "→ result" in result
        assert "format_result" in result
        assert "→ display" in result

    def test_empty_registry(self) -> None:
        """Empty registry returns empty string."""
        from bricks.core.schema import output_key_table

        reg = BrickRegistry()
        assert output_key_table(reg) == ""


class TestLiteralAnnotation:
    """Tests for Literal type formatting in signatures (Mission 077)."""

    def test_literal_annotation_formatted_cleanly(self) -> None:
        """_format_annotation(Literal["sum", "avg"]) returns '"sum"|"avg"'."""
        from typing import Literal

        from bricks.core.schema import _format_annotation

        result = _format_annotation(Literal["sum", "avg"])
        assert result == "'sum'|'avg'", f"Expected \"'sum'|'avg'\", got {result!r}"

    def test_format_annotation_standard_type(self) -> None:
        """_format_annotation(str) returns 'str'."""
        from bricks.core.schema import _format_annotation

        assert _format_annotation(str) == "str"
        assert _format_annotation(int) == "int"

    def test_compact_signatures_include_literal_values(self) -> None:
        """compact_brick_signatures() emits Literal values for bricks that declare them."""
        from typing import Literal

        reg = BrickRegistry()

        @brick(tags=["test"], description="Aggregate values.")
        def aggregate(data: list, operation: Literal["sum", "avg", "min"]) -> dict:  # type: ignore[type-arg]
            """Aggregate."""
            return {"result": 0}

        reg.register("aggregate", aggregate, aggregate.__brick_meta__)
        result = compact_brick_signatures(reg)
        assert "'sum'|'avg'|'min'" in result, f"Expected Literal values in signatures, got:\n{result}"
