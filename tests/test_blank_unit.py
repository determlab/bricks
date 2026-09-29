"""A blank unit id is refused by ``bricks run --unit`` and ``run_for_unit`` (#82)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from bricks import run_for_unit
from bricks.cli.main import app

_BLUEPRINT = Path(__file__).resolve().parent.parent / "blueprints" / "psu_limits.yaml"
_INPUTS = ["-i", "vout=5.0", "-i", "iout=0.4", "-i", "ripple_pp=12"]


def test_cli_blank_unit_json() -> None:
    result = CliRunner().invoke(app, ["run", str(_BLUEPRINT), "--unit", " ", "--json", *_INPUTS])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["type"] == "InvalidInputError"
    assert "--unit must not be blank" in payload["error"]["message"]
    assert "leave it out" in payload["error"]["message"]


def test_cli_blank_unit_text() -> None:
    result = CliRunner().invoke(app, ["run", str(_BLUEPRINT), "--unit", " ", *_INPUTS])
    assert result.exit_code == 1
    assert "--unit must not be blank" in result.output


def test_run_for_unit_blank_unit_is_error_outcome() -> None:
    outcome = run_for_unit(_BLUEPRINT, inputs={"vout": 5.0, "iout": 0.4, "ripple_pp": 12}, unit=" ")
    assert outcome.verdict.status == "error"
    assert "blank" in (outcome.verdict.detail or "")
