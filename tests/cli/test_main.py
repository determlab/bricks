"""Tests for bricks.cli.main."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from bricks.cli.main import app

runner = CliRunner()


class TestCLI:
    """Existing CLI smoke tests."""

    def test_help_exits_zero(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"

    def test_no_args_shows_help(self) -> None:
        result = runner.invoke(app, [])
        assert "Usage" in result.output, f"Expected 'Usage' in output, got {result.output!r}"


class TestInitCommand:
    """Tests for the `init` command."""

    def test_init_creates_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert (tmp_path / "bricks.config.yaml").exists(), "Expected bricks.config.yaml to exist"
        assert (tmp_path / "blueprints").is_dir(), "Expected blueprints/ to be a directory"
        assert (tmp_path / "bricks_lib").is_dir(), "Expected bricks_lib/ to be a directory"
        assert (tmp_path / "bricks_lib" / "__init__.py").exists(), "Expected bricks_lib/__init__.py to exist"

    def test_init_output_messages(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert "bricks.config.yaml" in result.output, "Expected 'bricks.config.yaml' in output"
        assert "blueprints" in result.output, "Expected 'blueprints' in output"
        assert "bricks_lib" in result.output, "Expected 'bricks_lib' in output"
        assert "initialised" in result.output, "Expected 'initialised' in output"

    def test_init_config_content(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        content = (tmp_path / "bricks.config.yaml").read_text()
        assert "version" in content, "Expected 'version' in config content"
        assert "auto_discover" in content, "Expected 'auto_discover' in config content"
        assert "sequences" in content, "Expected 'sequences' in config content"

    def test_init_fails_if_config_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "bricks.config.yaml").write_text("version: '1'\n")
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}"

    def test_init_error_message_on_existing_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "bricks.config.yaml").write_text("version: '1'\n")
        result = runner.invoke(app, ["init"])
        assert "already exists" in result.output, "Expected 'already exists' in output"

    def test_init_idempotent_directories(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """init succeeds even if blueprints/ and bricks_lib/ already exist."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "blueprints").mkdir()
        (tmp_path / "bricks_lib").mkdir()
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"


class TestNewBrickCommand:
    """Tests for the `new brick` command."""

    def test_new_brick_creates_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        bricks_lib = tmp_path / "bricks_lib"
        bricks_lib.mkdir()
        result = runner.invoke(app, ["new", "brick", "my_test_brick"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        brick_file = bricks_lib / "my_test_brick.py"
        assert brick_file.exists(), f"Expected {brick_file} to exist"

    def test_new_brick_content_has_class(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "bricks_lib").mkdir()
        runner.invoke(app, ["new", "brick", "my_test_brick"])
        content = (tmp_path / "bricks_lib" / "my_test_brick.py").read_text()
        assert "class MyTestBrick(BaseBrick)" in content, "Expected class definition in content"
        assert 'name = "my_test_brick"' in content, "Expected name attribute in content"
        assert "def execute" in content, "Expected execute method in content"

    def test_new_brick_normalises_name_hyphens(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "bricks_lib").mkdir()
        result = runner.invoke(app, ["new", "brick", "My-Brick"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert (tmp_path / "bricks_lib" / "my_brick.py").exists(), "Expected my_brick.py to exist"

    def test_new_brick_normalises_name_uppercase(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "bricks_lib").mkdir()
        result = runner.invoke(app, ["new", "brick", "ReadTemperature"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert (tmp_path / "bricks_lib" / "readtemperature.py").exists(), "Expected readtemperature.py to exist"

    def test_new_brick_creates_parent_dirs(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """new brick creates bricks_lib/ if it does not exist."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["new", "brick", "auto_make"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert (tmp_path / "bricks_lib" / "auto_make.py").exists(), "Expected auto_make.py to exist"

    def test_new_brick_output_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "bricks_lib").mkdir()
        result = runner.invoke(app, ["new", "brick", "sample"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert "sample.py" in result.output, "Expected 'sample.py' in output"

    def test_new_brick_has_imports(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "bricks_lib").mkdir()
        runner.invoke(app, ["new", "brick", "import_check"])
        content = (tmp_path / "bricks_lib" / "import_check.py").read_text()
        assert "from bricks.core import" in content, "Expected bricks.core import in content"
        assert "BaseBrick" in content, "Expected BaseBrick in content"
        assert "BrickMeta" in content, "Expected BrickMeta in content"
        assert "BrickModel" in content, "Expected BrickModel in content"


class TestNewBlueprintCommand:
    """Tests for the `new blueprint` command."""

    def test_new_blueprint_creates_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["new", "blueprint", "power_cycle"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        bp_file = tmp_path / "blueprints" / "power_cycle.yaml"
        assert bp_file.exists(), f"Expected {bp_file} to exist"

    def test_new_blueprint_content(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["new", "blueprint", "power_cycle"])
        content = (tmp_path / "blueprints" / "power_cycle.yaml").read_text()
        assert "name: power_cycle" in content, "Expected 'name: power_cycle' in content"
        assert "steps:" in content, "Expected 'steps:' in content"

    def test_new_blueprint_normalises_hyphens(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["new", "blueprint", "my-cool-blueprint"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert (tmp_path / "blueprints" / "my_cool_blueprint.yaml").exists(), "Expected my_cool_blueprint.yaml to exist"

    def test_new_blueprint_uses_config_base_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "bricks.config.yaml").write_text("sequences:\n  base_dir: 'my_bps/'\n")
        result = runner.invoke(app, ["new", "blueprint", "test_bp"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert (tmp_path / "my_bps" / "test_bp.yaml").exists(), "Expected test_bp.yaml in my_bps/"

    def test_new_blueprint_output_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["new", "blueprint", "foo"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert "foo.yaml" in result.output, "Expected 'foo.yaml' in output"

    def test_new_blueprint_outputs_map(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["new", "blueprint", "check_outputs"])
        content = (tmp_path / "blueprints" / "check_outputs.yaml").read_text()
        assert "outputs_map:" in content, "Expected 'outputs_map:' in content"


class TestNewSequenceCommand:
    """Tests for the `new sequence` command (alias for 'new blueprint')."""

    def test_new_sequence_creates_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["new", "sequence", "power_cycle"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        # Creates in blueprints/ (default base_dir)
        bp_file = tmp_path / "blueprints" / "power_cycle.yaml"
        assert bp_file.exists(), f"Expected {bp_file} to exist"

    def test_new_sequence_content(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["new", "sequence", "power_cycle"])
        content = (tmp_path / "blueprints" / "power_cycle.yaml").read_text()
        assert "name: power_cycle" in content, "Expected 'name: power_cycle' in content"
        assert "steps:" in content, "Expected 'steps:' in content"

    def test_new_sequence_normalises_hyphens(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["new", "sequence", "my-cool-sequence"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert (tmp_path / "blueprints" / "my_cool_sequence.yaml").exists(), "Expected my_cool_sequence.yaml to exist"

    def test_new_sequence_uses_config_base_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "bricks.config.yaml").write_text("sequences:\n  base_dir: 'my_seqs/'\n")
        result = runner.invoke(app, ["new", "sequence", "test_seq"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert (tmp_path / "my_seqs" / "test_seq.yaml").exists(), "Expected test_seq.yaml in my_seqs/"

    def test_new_sequence_output_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["new", "sequence", "foo"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert "foo.yaml" in result.output, "Expected 'foo.yaml' in output"

    def test_new_sequence_outputs_map(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["new", "sequence", "check_outputs"])
        content = (tmp_path / "blueprints" / "check_outputs.yaml").read_text()
        assert "outputs_map:" in content, "Expected 'outputs_map:' in content"


class TestCheckCommand:
    """Tests for the `check` command."""

    def _make_valid_blueprint(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
        """Create a bricks_lib with a registered brick and a valid blueprint file."""
        monkeypatch.chdir(tmp_path)
        bricks_lib = tmp_path / "bricks_lib"
        bricks_lib.mkdir()
        (bricks_lib / "adder.py").write_text(
            "from bricks.core import brick\n\n"
            "@brick(description='Add two numbers')\n"
            "def add(a: int, b: int) -> int:\n"
            "    return a + b\n"
        )
        (tmp_path / "bricks.config.yaml").write_text(
            "registry:\n  auto_discover: true\n  paths:\n    - 'bricks_lib/'\n"
        )
        bp_file = tmp_path / "add_bp.yaml"
        bp_file.write_text(
            "name: add_bp\n"
            "steps:\n"
            "  - name: do_add\n"
            "    brick: add\n"
            "    params:\n"
            "      a: 1\n"
            "      b: 2\n"
            "    save_as: result\n"
            "outputs_map:\n"
            "  total: '${result}'\n"
        )
        return bricks_lib, bp_file

    def test_check_valid_blueprint(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _, bp_file = self._make_valid_blueprint(tmp_path, monkeypatch)
        result = runner.invoke(app, ["check", str(bp_file)])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert "valid" in result.output, "Expected 'valid' in output"

    def test_check_missing_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["check", "nonexistent.yaml"])
        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}"

    def test_check_missing_file_error_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["check", "nonexistent.yaml"])
        assert "not found" in result.output, "Expected 'not found' in output"

    def test_check_invalid_yaml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("invalid: yaml: [unclosed")
        result = runner.invoke(app, ["check", str(bad_file)])
        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}"

    def test_check_unknown_brick_fails(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        bp_file = tmp_path / "unknown_brick.yaml"
        bp_file.write_text("name: test_bp\nsteps:\n  - name: s1\n    brick: does_not_exist\n")
        result = runner.invoke(app, ["check", str(bp_file)])
        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}"

    def test_check_empty_blueprint_fails(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        bp_file = tmp_path / "empty.yaml"
        bp_file.write_text("name: empty_bp\nsteps: []\n")
        result = runner.invoke(app, ["check", str(bp_file)])
        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}"


class TestDryRunCommand:
    """Tests for the `dry-run` command."""

    def _make_valid_blueprint(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        monkeypatch.chdir(tmp_path)
        bricks_lib = tmp_path / "bricks_lib"
        bricks_lib.mkdir()
        (bricks_lib / "greeter.py").write_text(
            "from bricks.core import brick\n\n"
            "@brick(description='Greet')\n"
            "def greet(name: str) -> str:\n"
            "    return f'Hello {name}'\n"
        )
        (tmp_path / "bricks.config.yaml").write_text(
            "registry:\n  auto_discover: true\n  paths:\n    - 'bricks_lib/'\n"
        )
        bp_file = tmp_path / "greet.yaml"
        bp_file.write_text(
            "name: greet_bp\n"
            "steps:\n"
            "  - name: say_hello\n"
            "    brick: greet\n"
            "    params:\n"
            "      name: world\n"
            "    save_as: greeting\n"
            "outputs_map:\n"
            "  message: '${greeting}'\n"
        )
        return bp_file

    def test_dry_run_valid_blueprint(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        bp_file = self._make_valid_blueprint(tmp_path, monkeypatch)
        result = runner.invoke(app, ["dry-run", str(bp_file)])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert "valid" in result.output.lower(), "Expected 'valid' in output"

    def test_dry_run_valid_message_contains_passed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        bp_file = self._make_valid_blueprint(tmp_path, monkeypatch)
        result = runner.invoke(app, ["dry-run", str(bp_file)])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert "passed" in result.output.lower(), "Expected 'passed' in output"

    def test_dry_run_missing_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["dry-run", "nonexistent.yaml"])
        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}"

    def test_dry_run_missing_file_error_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["dry-run", "nonexistent.yaml"])
        assert "not found" in result.output, "Expected 'not found' in output"

    def test_dry_run_unknown_brick_fails(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        bp_file = tmp_path / "unknown.yaml"
        bp_file.write_text("name: test_bp\nsteps:\n  - name: s1\n    brick: unknown_brick\n")
        result = runner.invoke(app, ["dry-run", str(bp_file)])
        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}"

    def test_dry_run_invalid_yaml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("name: [unclosed")
        result = runner.invoke(app, ["dry-run", str(bad_file)])
        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}"


class TestRunCommand:
    """Tests for the `run` command."""

    def _make_runnable_blueprint(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        monkeypatch.chdir(tmp_path)
        bricks_lib = tmp_path / "bricks_lib"
        bricks_lib.mkdir()
        (bricks_lib / "math_ops.py").write_text(
            "from bricks.core import brick\n\n"
            "@brick(description='Double a number')\n"
            "def double(x: int) -> int:\n"
            "    return x * 2\n"
        )
        (tmp_path / "bricks.config.yaml").write_text(
            "registry:\n  auto_discover: true\n  paths:\n    - 'bricks_lib/'\n"
        )
        bp_file = tmp_path / "double_bp.yaml"
        bp_file.write_text(
            "name: double_bp\n"
            "inputs:\n"
            "  x: int\n"
            "steps:\n"
            "  - name: do_double\n"
            "    brick: double\n"
            "    params:\n"
            "      x: '${inputs.x}'\n"
            "    save_as: doubled\n"
            "outputs_map:\n"
            "  result: '${doubled}'\n"
        )
        return bp_file

    def test_run_missing_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["run", "nonexistent.yaml"])
        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}"

    def test_run_missing_file_error_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["run", "nonexistent.yaml"])
        assert "not found" in result.output, "Expected 'not found' in output"

    def test_run_invalid_input_format(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        bp_file = self._make_runnable_blueprint(tmp_path, monkeypatch)
        result = runner.invoke(app, ["run", str(bp_file), "--input", "no_equals"])
        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}"
        assert "key=value" in result.output, "Expected 'key=value' in output"

    def test_run_invalid_yaml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("name: [unclosed")
        result = runner.invoke(app, ["run", str(bad_file)])
        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}"

    def test_run_completes_success(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        bp_file = self._make_runnable_blueprint(tmp_path, monkeypatch)
        result = runner.invoke(app, ["run", str(bp_file), "--input", "x=5"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert "completed" in result.output, "Expected 'completed' in output"

    def test_run_outputs_shown(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        bp_file = self._make_runnable_blueprint(tmp_path, monkeypatch)
        result = runner.invoke(app, ["run", str(bp_file), "--input", "x=3"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert "Outputs:" in result.output, "Expected 'Outputs:' in output"

    def test_run_input_json_parsing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Numeric inputs are parsed as JSON (int/float)."""
        bp_file = self._make_runnable_blueprint(tmp_path, monkeypatch)
        result = runner.invoke(app, ["run", str(bp_file), "--input", "x=7"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"

    def test_run_no_outputs_map(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        bricks_lib = tmp_path / "bricks_lib"
        bricks_lib.mkdir()
        (bricks_lib / "noop.py").write_text(
            "from bricks.core import brick\n\n@brick()\ndef noop() -> None:\n    pass\n"
        )
        (tmp_path / "bricks.config.yaml").write_text(
            "registry:\n  auto_discover: true\n  paths:\n    - 'bricks_lib/'\n"
        )
        bp_file = tmp_path / "noop_bp.yaml"
        bp_file.write_text("name: noop_bp\nsteps:\n  - name: do_noop\n    brick: noop\n")
        result = runner.invoke(app, ["run", str(bp_file)])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert "completed" in result.output, "Expected 'completed' in output"


class TestListCommand:
    """Tests for the `list` command."""

    def test_list_empty_registry(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert "No bricks registered" in result.output, "Expected 'No bricks registered' in output"

    def test_list_with_auto_discover(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        bricks_lib = tmp_path / "bricks_lib"
        bricks_lib.mkdir()
        (bricks_lib / "my_brick.py").write_text(
            "from bricks.core import brick\n\n"
            "@brick(description='Add numbers')\n"
            "def add_numbers(a: int, b: int) -> int:\n"
            "    return a + b\n"
        )
        (tmp_path / "bricks.config.yaml").write_text(
            "registry:\n  auto_discover: true\n  paths:\n    - 'bricks_lib/'\n"
        )
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert "add_numbers" in result.output, "Expected 'add_numbers' in output"

    def test_list_shows_brick_count(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        bricks_lib = tmp_path / "bricks_lib"
        bricks_lib.mkdir()
        (bricks_lib / "b1.py").write_text("from bricks.core import brick\n\n@brick()\ndef brick_one() -> None: pass\n")
        (bricks_lib / "b2.py").write_text("from bricks.core import brick\n\n@brick()\ndef brick_two() -> None: pass\n")
        (tmp_path / "bricks.config.yaml").write_text(
            "registry:\n  auto_discover: true\n  paths:\n    - 'bricks_lib/'\n"
        )
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert "2" in result.output, "Expected '2' in output"

    def test_list_shows_description(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        bricks_lib = tmp_path / "bricks_lib"
        bricks_lib.mkdir()
        (bricks_lib / "described.py").write_text(
            "from bricks.core import brick\n\n@brick(description='A useful brick')\ndef useful_brick() -> None: pass\n"
        )
        (tmp_path / "bricks.config.yaml").write_text(
            "registry:\n  auto_discover: true\n  paths:\n    - 'bricks_lib/'\n"
        )
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert "A useful brick" in result.output, "Expected 'A useful brick' in output"

    def test_list_shows_destructive_tag(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        bricks_lib = tmp_path / "bricks_lib"
        bricks_lib.mkdir()
        (bricks_lib / "dangerous.py").write_text(
            "from bricks.core import brick\n\n@brick(destructive=True)\ndef destroy_all() -> None: pass\n"
        )
        (tmp_path / "bricks.config.yaml").write_text(
            "registry:\n  auto_discover: true\n  paths:\n    - 'bricks_lib/'\n"
        )
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert "DESTRUCTIVE" in result.output, "Expected 'DESTRUCTIVE' in output"

    def test_list_shows_tags(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        bricks_lib = tmp_path / "bricks_lib"
        bricks_lib.mkdir()
        (bricks_lib / "tagged.py").write_text(
            "from bricks.core import brick\n\n@brick(tags=['hardware', 'sensor'])\ndef read_sensor() -> None: pass\n"
        )
        (tmp_path / "bricks.config.yaml").write_text(
            "registry:\n  auto_discover: true\n  paths:\n    - 'bricks_lib/'\n"
        )
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert "hardware" in result.output, "Expected 'hardware' in output"
        assert "sensor" in result.output, "Expected 'sensor' in output"


class TestComposeCommand:
    """Tests for the `compose` command's AI-layer gating.

    Full compose behavior is tested in the bricks-ai repo; here we only
    verify the engine-side gate fails fast with an install hint.
    """

    def test_compose_without_ai_extra_exits_with_hint(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """compose exits 1 with an install hint when litellm is unavailable."""
        import importlib.util

        monkeypatch.chdir(tmp_path)
        real_find_spec = importlib.util.find_spec

        def fake_find_spec(name: str, *args: object, **kwargs: object) -> object:
            if name == "litellm":
                return None
            return real_find_spec(name, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
        result = runner.invoke(app, ["compose", "do something"])
        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}"
        assert "bricks-ai[ai]" in result.output, f"Expected install hint in output, got {result.output!r}"


class TestSetupRegistry:
    """Tests for the _setup_registry helper."""

    def test_setup_registry_returns_empty_by_default(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from bricks.cli.main import _setup_registry

        monkeypatch.chdir(tmp_path)
        registry, config = _setup_registry()
        assert registry.list_all() == [], f"Expected empty registry, got {registry.list_all()!r}"
        assert config.registry.auto_discover is False, (
            f"Expected auto_discover=False, got {config.registry.auto_discover!r}"
        )

    def test_setup_registry_auto_discover(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from bricks.cli.main import _setup_registry

        monkeypatch.chdir(tmp_path)
        bricks_lib = tmp_path / "bricks_lib"
        bricks_lib.mkdir()
        (bricks_lib / "example.py").write_text(
            "from bricks.core import brick\n\n@brick()\ndef example_fn() -> None: pass\n"
        )
        (tmp_path / "bricks.config.yaml").write_text(
            "registry:\n  auto_discover: true\n  paths:\n    - 'bricks_lib/'\n"
        )
        registry, config = _setup_registry(config_dir=tmp_path)
        assert config.registry.auto_discover is True, (
            f"Expected auto_discover=True, got {config.registry.auto_discover!r}"
        )
        names = [n for n, _ in registry.list_all()]
        assert "example_fn" in names, f"Expected 'example_fn' in {names!r}"

    def test_setup_registry_skips_nonexistent_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from bricks.cli.main import _setup_registry

        monkeypatch.chdir(tmp_path)
        (tmp_path / "bricks.config.yaml").write_text(
            "registry:\n  auto_discover: true\n  paths:\n    - 'nonexistent_dir/'\n"
        )
        registry, _ = _setup_registry(config_dir=tmp_path)
        # Should not raise; just skip the nonexistent path
        assert registry.list_all() == [], f"Expected empty registry, got {registry.list_all()!r}"
