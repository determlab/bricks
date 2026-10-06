"""``bricks run`` and ``run_for_unit`` validate the blueprint before the first
step (G8, bricks#87). A blueprint with a counting brick in step 1 and an
unknown brick in step 2 proves it: the counter must stay 0 through both
entry points, because the unknown reference in step 2 is caught before step
1 ever runs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bricks.cli.main import app
from bricks.core.brick import brick
from bricks.core.registry import BrickRegistry
from bricks.outcome import run_for_unit

runner = CliRunner()

_counter = {"n": 0}


@brick()
def count(x: int) -> dict[str, int]:
    """Count a call. Returns {result: x}."""
    _counter["n"] += 1
    return {"result": x}


def _registry_with_count() -> BrickRegistry:
    reg = BrickRegistry()
    reg.register("count", count, count.__brick_meta__)  # type: ignore[attr-defined]
    return reg


# Step 1 runs `count` (if reached); step 2 names a brick that does not exist.
# A validate-first entry point never reaches step 1, so the counter stays 0.
_INVALID_BLUEPRINT = (
    "name: invalid\n"
    "steps:\n"
    "  - name: s1\n"
    "    brick: count\n"
    "    params: {x: 1}\n"
    "  - name: s2\n"
    "    brick: no_such_brick\n"
    "    params: {}\n"
)


@pytest.fixture(autouse=True)
def _reset_counter() -> None:
    _counter["n"] = 0


def test_run_for_unit_stops_before_step_1() -> None:
    out = run_for_unit(_INVALID_BLUEPRINT, registry=_registry_with_count())
    assert out.verdict.status == "error"
    assert out.result is None
    assert _counter["n"] == 0


def test_bricks_run_cli_stops_before_step_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("bricks.cli.main.build_default_registry", _registry_with_count)
    bp_path = tmp_path / "invalid.yaml"
    bp_path.write_text(_INVALID_BLUEPRINT, encoding="utf-8")

    result = runner.invoke(app, ["run", str(bp_path), "--json"])
    assert result.exit_code == 3, result.output
    doc = json.loads(result.stdout)
    assert doc["ok"] is False
    assert doc["verdict"] == "error"
    assert doc["error"]["type"] == "BlueprintValidationError"
    assert doc["error"]["message"]
    assert doc["error"]["fix"]
    assert _counter["n"] == 0


def test_bricks_run_cli_text_mode_also_stops_before_step_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("bricks.cli.main.build_default_registry", _registry_with_count)
    bp_path = tmp_path / "invalid.yaml"
    bp_path.write_text(_INVALID_BLUEPRINT, encoding="utf-8")

    result = runner.invoke(app, ["run", str(bp_path)])
    assert result.exit_code == 3, result.output
    assert _counter["n"] == 0
