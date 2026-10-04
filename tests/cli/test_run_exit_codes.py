"""`bricks run` exit codes: 0 pass, 1 fail (a failing check), 2 usage, 3 error (a broken run) (#101)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bricks.cli.main import app

_BLUEPRINTS = Path(__file__).resolve().parent.parent.parent / "blueprints"
_CRM = str(_BLUEPRINTS / "crm_pipeline.yaml")
_PSU = str(_BLUEPRINTS / "psu_limits.yaml")
_ROW = '[{"status": "active", "monthly_revenue": 4200}]'


def _psu_inputs(vout: str) -> list[str]:
    return ["-i", f"vout={vout}", "-i", "iout=0.4", "-i", "ripple_pp=12"]


@pytest.mark.parametrize("json_flag", [[], ["--json"]])
def test_pass_exits_0(json_flag: list[str]) -> None:
    result = CliRunner().invoke(app, ["run", _CRM, "-i", f"crm_json={_ROW}", *json_flag])
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("json_flag", [[], ["--json"]])
def test_failing_check_exits_1(json_flag: list[str]) -> None:
    result = CliRunner().invoke(app, ["run", _PSU, *_psu_inputs("4.7"), *json_flag])
    assert result.exit_code == 1, result.output


@pytest.mark.parametrize("json_flag", [[], ["--json"]])
def test_error_verdict_exits_3(json_flag: list[str]) -> None:
    result = CliRunner().invoke(app, ["run", _CRM, "-i", "crm_json=[]", *json_flag])
    assert result.exit_code == 3, result.output
    if json_flag:
        payload = json.loads(result.stdout)
        assert payload["verdict"] == "error"
        assert "Division by zero" in payload["error"]["message"]
    else:
        assert "Verdict: ERROR" in result.output
