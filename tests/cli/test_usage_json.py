"""Usage errors print one JSON document with ``--json``, and ``bricks --version`` works (#94)."""

from __future__ import annotations

import json
import re

import pytest
from typer.testing import CliRunner

from bricks.cli.main import app

runner = CliRunner()


@pytest.mark.parametrize(
    "args",
    [["run"], ["check"], ["run", "x.yaml", "--bogus"]],
)
def test_usage_error_is_json_with_json_flag(args: list[str]) -> None:
    result = runner.invoke(app, [*args, "--json"])
    assert result.exit_code == 2
    doc = json.loads(result.stdout)
    assert doc["ok"] is False
    assert doc["error"]["type"] == "UsageError"
    assert "--help" in doc["error"]["message"]
    assert "fix" not in doc["error"]


@pytest.mark.parametrize("args", [["run"], ["check"], ["run", "x.yaml", "--bogus"]])
def test_usage_error_stdout_empty_without_json_flag(args: list[str]) -> None:
    result = runner.invoke(app, args)
    assert result.exit_code == 2
    assert result.stdout == ""


def test_failing_json_command_exits_3_on_error_verdict() -> None:
    result = runner.invoke(app, ["run", "blueprints/psu_limits.yaml", "--json"])
    assert result.exit_code == 3
    assert json.loads(result.stdout)["ok"] is False


def test_passing_json_command_exits_0() -> None:
    result = runner.invoke(app, ["check", "blueprints/psu_limits.yaml", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["ok"] is True


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert re.match(r"^bricks-engine \d+\.\d+\.\d+", result.stdout)
