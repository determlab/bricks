"""Tests for bricks store seed CLI command."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from bricks.cli.main import app

runner = CliRunner()


def _make_valid_yaml(name: str) -> str:
    """Return a minimal valid blueprint YAML.

    Args:
        name: Blueprint name to use.

    Returns:
        YAML string representing a minimal valid blueprint.
    """
    return f"""name: {name}
steps:
  - name: step1
    brick: divide
    params:
      a: 10.0
      b: 2.0
    save_as: result
outputs_map:
  total: "${{result.result}}"
"""


class TestStoreSeed:
    """Tests for the ``bricks store seed`` command."""

    def test_seed_loads_yaml_files(self, tmp_path: Path) -> None:
        """Seed command loads YAML files from a directory."""
        (tmp_path / "bp1.yaml").write_text(_make_valid_yaml("bp1"), encoding="utf-8")
        (tmp_path / "bp2.yaml").write_text(_make_valid_yaml("bp2"), encoding="utf-8")
        store_dir = tmp_path / "store"
        result = runner.invoke(app, ["store", "seed", str(tmp_path), "--store", str(store_dir)])
        assert result.exit_code == 0, f"Unexpected exit code: {result.exit_code}\n{result.output}"
        assert "2 loaded" in result.output

    def test_seed_skips_invalid_yaml(self, tmp_path: Path) -> None:
        """Seed command skips invalid YAML files without crashing."""
        (tmp_path / "valid.yaml").write_text(_make_valid_yaml("valid_bp"), encoding="utf-8")
        (tmp_path / "bad.yaml").write_text("not: valid: yaml: [[[", encoding="utf-8")
        store_dir = tmp_path / "store"
        result = runner.invoke(app, ["store", "seed", str(tmp_path), "--store", str(store_dir)])
        assert result.exit_code == 0, f"Unexpected exit code: {result.exit_code}\n{result.output}"
        assert "1 loaded" in result.output

    def test_seed_missing_dir_exits_with_error(self, tmp_path: Path) -> None:
        """Seed command exits with error if directory not found."""
        result = runner.invoke(app, ["store", "seed", str(tmp_path / "nonexistent")])
        assert result.exit_code != 0

    def test_seed_reruns_update_existing(self, tmp_path: Path) -> None:
        """Seed command updates (overwrites) blueprints that already exist in the store."""
        (tmp_path / "bp1.yaml").write_text(_make_valid_yaml("bp1"), encoding="utf-8")
        store_dir = tmp_path / "store"
        # First seed
        result1 = runner.invoke(app, ["store", "seed", str(tmp_path), "--store", str(store_dir)])
        assert result1.exit_code == 0
        assert "1 loaded" in result1.output
        # Second seed — should update, not crash
        result2 = runner.invoke(app, ["store", "seed", str(tmp_path), "--store", str(store_dir)])
        assert result2.exit_code == 0
        assert "1 loaded" in result2.output
