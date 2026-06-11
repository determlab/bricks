"""Tests for sub-blueprint execution in BlueprintEngine and BlueprintValidator."""

from __future__ import annotations

from pathlib import Path

import pytest

from bricks.core.brick import brick
from bricks.core.engine import BlueprintEngine
from bricks.core.exceptions import BlueprintValidationError, BrickExecutionError
from bricks.core.loader import BlueprintLoader
from bricks.core.models import BlueprintDefinition, StepDefinition
from bricks.core.registry import BrickRegistry
from bricks.core.validation import BlueprintValidator

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_registry() -> BrickRegistry:
    """Build a registry with simple math bricks."""
    reg = BrickRegistry()

    @brick()
    def add(a: float, b: float) -> dict[str, float]:
        """Add two numbers."""
        return {"result": a + b}

    @brick()
    def multiply(a: float, b: float) -> dict[str, float]:
        """Multiply two numbers."""
        return {"result": a * b}

    @brick()
    def double(x: float) -> dict[str, float]:
        """Double a number."""
        return {"result": x * 2}

    for fn in (add, multiply, double):
        reg.register(fn.__brick_meta__.name, fn, fn.__brick_meta__)
    return reg


def _write_child_bp(tmp_path: Path, content: str, name: str = "child.yaml") -> Path:
    """Write a child blueprint YAML to a temp file and return its path."""
    p = tmp_path / name
    p.write_text(content)
    return p


# ── Model validator tests ─────────────────────────────────────────────────────


class TestStepDefinitionValidator:
    def test_neither_brick_nor_blueprint_raises(self) -> None:
        """StepDefinition with neither brick nor blueprint is invalid."""
        with pytest.raises(Exception, match=r"brick.*blueprint|blueprint.*brick"):
            StepDefinition(name="s1")

    def test_both_brick_and_blueprint_raises(self) -> None:
        """StepDefinition with both brick and blueprint is invalid."""
        with pytest.raises(Exception, match=r"brick.*blueprint|blueprint.*brick"):
            StepDefinition(name="s1", brick="add", blueprint="child.yaml")

    def test_brick_only_valid(self) -> None:
        """StepDefinition with only brick is valid."""
        step = StepDefinition(name="s1", brick="add")
        assert step.brick == "add"
        assert step.blueprint is None

    def test_blueprint_only_valid(self) -> None:
        """StepDefinition with only blueprint is valid."""
        step = StepDefinition(name="s1", blueprint="child.yaml")
        assert step.blueprint == "child.yaml"
        assert step.brick is None


# ── Engine sub-blueprint tests ────────────────────────────────────────────────


class TestSubBlueprintExecution:
    def test_sub_blueprint_runs_and_returns_outputs(self, tmp_path: Path) -> None:
        """Sub-blueprint step executes and returns child outputs."""
        child = _write_child_bp(
            tmp_path,
            """
name: child
steps:
  - name: c1
    brick: add
    params:
      a: 1.0
      b: 2.0
    save_as: sum
outputs_map:
  total: "${sum.result}"
""",
        )

        reg = _make_registry()
        loader = BlueprintLoader()
        engine = BlueprintEngine(registry=reg, loader=loader)

        parent = BlueprintDefinition(
            name="parent",
            steps=[StepDefinition(name="sub", blueprint=str(child), save_as="child_result")],
            outputs_map={"answer": "${child_result.total}"},
        )

        result = engine.run(parent).outputs
        assert result["answer"] == 3.0, f"Expected 3.0, got {result['answer']!r}"

    def test_sub_blueprint_result_accessible_by_parent(self, tmp_path: Path) -> None:
        """Parent step can reference sub-blueprint output via save_as."""
        child = _write_child_bp(
            tmp_path,
            """
name: child
steps:
  - name: c1
    brick: double
    params:
      x: 5.0
    save_as: doubled
outputs_map:
  value: "${doubled.result}"
""",
        )

        reg = _make_registry()
        engine = BlueprintEngine(registry=reg)
        parent = BlueprintDefinition(
            name="parent",
            steps=[
                StepDefinition(name="sub", blueprint=str(child), save_as="r"),
                StepDefinition(
                    name="final",
                    brick="add",
                    params={"a": "${r.value}", "b": 1.0},
                    save_as="total",
                ),
            ],
            outputs_map={"result": "${total.result}"},
        )

        result = engine.run(parent).outputs
        assert result["result"] == 11.0, f"Expected 11.0, got {result['result']!r}"

    def test_parent_params_passed_as_child_inputs(self, tmp_path: Path) -> None:
        """Parent step params become child blueprint inputs."""
        child = _write_child_bp(
            tmp_path,
            """
name: child
inputs:
  x: float
  y: float
steps:
  - name: c1
    brick: add
    params:
      a: "${inputs.x}"
      b: "${inputs.y}"
    save_as: sum
outputs_map:
  total: "${sum.result}"
""",
        )

        reg = _make_registry()
        engine = BlueprintEngine(registry=reg)
        parent = BlueprintDefinition(
            name="parent",
            inputs={"a": "float", "b": "float"},
            steps=[
                StepDefinition(
                    name="sub",
                    blueprint=str(child),
                    params={"x": "${inputs.a}", "y": "${inputs.b}"},
                    save_as="r",
                )
            ],
            outputs_map={"result": "${r.total}"},
        )

        result = engine.run(parent, inputs={"a": 3.0, "b": 4.0}).outputs
        assert result["result"] == 7.0, f"Expected 7.0, got {result['result']!r}"

    def test_chained_after_sub_blueprint(self, tmp_path: Path) -> None:
        """Parent can chain brick steps after a sub-blueprint step."""
        child = _write_child_bp(
            tmp_path,
            """
name: child
steps:
  - name: c1
    brick: add
    params:
      a: 10.0
      b: 5.0
    save_as: s
outputs_map:
  val: "${s.result}"
""",
        )

        reg = _make_registry()
        engine = BlueprintEngine(registry=reg)
        parent = BlueprintDefinition(
            name="parent",
            steps=[
                StepDefinition(name="sub", blueprint=str(child), save_as="child_out"),
                StepDefinition(
                    name="double_it",
                    brick="double",
                    params={"x": "${child_out.val}"},
                    save_as="final",
                ),
            ],
            outputs_map={"result": "${final.result}"},
        )

        result = engine.run(parent).outputs
        assert result["result"] == 30.0, f"Expected 30.0, got {result['result']!r}"

    def test_file_not_found_raises_brick_execution_error(self) -> None:
        """Missing sub-blueprint file raises BrickExecutionError."""
        reg = _make_registry()
        engine = BlueprintEngine(registry=reg)
        parent = BlueprintDefinition(
            name="parent",
            steps=[StepDefinition(name="sub", blueprint="/nonexistent/path/child.yaml")],
        )

        with pytest.raises(BrickExecutionError):
            engine.run(parent)

    def test_recursion_depth_exceeded_raises(self, tmp_path: Path) -> None:
        """Exceeding max recursion depth raises BrickExecutionError."""
        # A blueprint that calls itself
        self_path = tmp_path / "self_ref.yaml"
        self_path.write_text(f"""
name: self_ref
steps:
  - name: recurse
    blueprint: "{self_path.as_posix()}"
""")

        reg = _make_registry()
        engine = BlueprintEngine(registry=reg)
        parent = BlueprintDefinition(
            name="parent",
            steps=[StepDefinition(name="sub", blueprint=str(self_path))],
        )

        with pytest.raises(BrickExecutionError):
            engine.run(parent)


# ── Validator sub-blueprint tests ─────────────────────────────────────────────


class TestValidatorSubBlueprint:
    def test_validator_passes_when_sub_blueprint_file_exists(self, tmp_path: Path) -> None:
        """Validator passes when sub-blueprint file exists."""
        child = _write_child_bp(tmp_path, "name: child\nsteps: []\n")

        reg = _make_registry()
        validator = BlueprintValidator(registry=reg)
        parent = BlueprintDefinition(
            name="parent",
            steps=[StepDefinition(name="sub", blueprint=str(child), save_as="r")],
        )
        validator.validate(parent)  # should not raise

    def test_validator_errors_when_sub_blueprint_file_missing(self) -> None:
        """Validator reports error when sub-blueprint file is not found."""
        reg = _make_registry()
        validator = BlueprintValidator(registry=reg)
        parent = BlueprintDefinition(
            name="parent",
            steps=[StepDefinition(name="sub", blueprint="/no/such/file.yaml", save_as="r")],
        )

        with pytest.raises(BlueprintValidationError) as exc_info:
            validator.validate(parent)
        assert any("not found" in e for e in exc_info.value.errors), (
            f"Expected 'not found' in errors: {exc_info.value.errors!r}"
        )

    def test_validator_mixed_brick_and_sub_blueprint_steps(self, tmp_path: Path) -> None:
        """Validator handles a blueprint mixing brick and sub-blueprint steps."""
        child = _write_child_bp(tmp_path, "name: child\nsteps: []\n")
        reg = _make_registry()
        validator = BlueprintValidator(registry=reg)
        parent = BlueprintDefinition(
            name="parent",
            steps=[
                StepDefinition(name="s1", brick="add", params={"a": 1.0, "b": 2.0}, save_as="r1"),
                StepDefinition(name="sub", blueprint=str(child), save_as="r2"),
            ],
        )
        validator.validate(parent)  # should not raise


def test_any_extra_output(tmp_path: Path) -> None:
    """Sub-blueprint with no outputs_map returns empty dict under save_as."""
    child = _write_child_bp(
        tmp_path,
        """
name: child
steps:
  - name: c1
    brick: add
    params:
      a: 1.0
      b: 1.0
""",
    )

    reg = _make_registry()
    engine = BlueprintEngine(registry=reg)
    parent = BlueprintDefinition(
        name="parent",
        steps=[StepDefinition(name="sub", blueprint=str(child), save_as="r")],
        outputs_map={"done": "${r}"},
    )
    result = engine.run(parent).outputs
    assert result["done"] == {}, f"Expected empty dict, got {result['done']!r}"
