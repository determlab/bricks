"""``bricks dry-run --json`` has the same shape as ``bricks check --json`` (#81).

The registry is a fixed one-brick registry, so the tests do not depend on
which packs are installed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bricks.cli.main import app
from bricks.core.brick import brick
from bricks.core.registry import BrickRegistry

_GOOD_BLUEPRINT = "name: x\nsteps:\n  - name: s\n    brick: add\n    params: {a: 1, b: 2}\n"
_BAD_BLUEPRINT = "name: x\nsteps:\n  - name: s\n    brick: nope\n    params: {}\n"

runner = CliRunner()


def _one_brick() -> BrickRegistry:
    @brick(description="Add two numbers.")
    def add(a: float, b: float) -> dict[str, float]:
        return {"result": a + b}

    reg = BrickRegistry()
    reg.register(add.__name__, add, add.__brick_meta__)  # type: ignore[attr-defined]
    return reg


@pytest.fixture(autouse=True)
def _fixed_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("bricks.cli.main.build_default_registry", _one_brick)


def _write(tmp_path: Path, text: str) -> str:
    p = tmp_path / "bp.yaml"
    p.write_text(text)
    return str(p)


def test_valid_file(tmp_path: Path) -> None:
    file = _write(tmp_path, _GOOD_BLUEPRINT)
    result = runner.invoke(app, ["dry-run", file, "--json"])
    assert result.exit_code == 0, result.stdout
    assert json.loads(result.stdout) == {"ok": True, "file": file, "errors": []}


def test_same_shape_as_check(tmp_path: Path) -> None:
    file = _write(tmp_path, _GOOD_BLUEPRINT)
    dry = runner.invoke(app, ["dry-run", file, "--json"])
    chk = runner.invoke(app, ["check", file, "--json"])
    assert json.loads(dry.stdout) == json.loads(chk.stdout)

    file = _write(tmp_path, _BAD_BLUEPRINT)
    dry = runner.invoke(app, ["dry-run", file, "--json"])
    chk = runner.invoke(app, ["check", file, "--json"])
    assert dry.exit_code == chk.exit_code == 1
    assert json.loads(dry.stdout) == json.loads(chk.stdout)


def test_missing_file(tmp_path: Path) -> None:
    missing = str(tmp_path / "nope.yaml")
    result = runner.invoke(app, ["dry-run", missing, "--json"])
    assert result.exit_code == 1
    doc = json.loads(result.stdout)
    assert doc["ok"] is False
    assert doc["file"] == missing
    assert len(doc["errors"]) == 1
    assert "File not found" in doc["errors"][0]


def test_bad_yaml(tmp_path: Path) -> None:
    result = runner.invoke(app, ["dry-run", _write(tmp_path, "name: [unclosed\n"), "--json"])
    assert result.exit_code == 1
    doc = json.loads(result.stdout)
    assert doc["ok"] is False
    assert doc["errors"][0].startswith("Error loading YAML")


def test_unknown_brick(tmp_path: Path) -> None:
    result = runner.invoke(app, ["dry-run", _write(tmp_path, _BAD_BLUEPRINT), "--json"])
    assert result.exit_code == 1
    doc = json.loads(result.stdout)
    assert doc["ok"] is False
    assert any("nope" in e for e in doc["errors"])


def test_text_output_unchanged(tmp_path: Path) -> None:
    result = runner.invoke(app, ["dry-run", _write(tmp_path, _GOOD_BLUEPRINT)])
    assert result.exit_code == 0
    assert result.stdout == "Blueprint 'x' is valid (dry-run passed).\n"


def test_help_shows_json() -> None:
    result = runner.invoke(app, ["dry-run", "--help"])
    assert "--json" in result.stdout
