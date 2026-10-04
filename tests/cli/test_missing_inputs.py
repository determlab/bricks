"""A run that lacks a declared input stops before the first step (#93)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from bricks import build_default_registry, run_for_unit
from bricks.core.brick import brick

BLUEPRINT = Path(__file__).resolve().parents[2] / "blueprints" / "psu_limits.yaml"

_CALLS: list[int] = []

_TWO_STEP_YAML = (
    "name: two_step\n"
    "inputs:\n"
    '  x: "int"\n'
    "steps:\n"
    "  - name: first\n"
    "    brick: record_call\n"
    "    params: {}\n"
    "  - name: second\n"
    "    brick: record_call\n"
    "    params: {}\n"
    "outputs_map: {}\n"
)


@brick()
def record_call() -> int:
    """Record that a step ran."""
    _CALLS.append(1)
    return len(_CALLS)


def test_cli_names_every_missing_input() -> None:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(  # noqa: S603  — fixed argv: this interpreter + a literal snippet + test args
        [
            sys.executable,
            "-c",
            "from bricks.cli.main import app; app(prog_name='bricks')",
            "run",
            str(BLUEPRINT),
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )
    assert result.returncode == 3, result.stderr
    doc = json.loads(result.stdout)
    assert doc["ok"] is False
    assert doc["verdict"] == "error"
    assert doc["error"]["type"] == "MissingInputError"
    message = doc["error"]["message"]
    for name in ("vout", "iout", "ripple_pp"):
        assert name in message
    assert "-i NAME=VALUE" in message


def test_run_for_unit_names_only_the_missing_inputs() -> None:
    out = run_for_unit(BLUEPRINT, inputs={"vout": 5.0})
    assert out.verdict.status == "error"
    assert out.error is not None
    assert str(out.error).startswith("missing input(s): iout, ripple_pp — ")


def test_run_for_unit_with_all_inputs_still_passes() -> None:
    out = run_for_unit(BLUEPRINT, inputs={"vout": 5.0, "iout": 0.4, "ripple_pp": 12})
    assert out.verdict.status == "pass"


def test_no_step_runs_when_an_input_is_missing() -> None:
    registry = build_default_registry()
    registry.register("record_call", record_call, record_call.__brick_meta__)
    _CALLS.clear()
    out = run_for_unit(_TWO_STEP_YAML, inputs={}, registry=registry)
    assert out.verdict.status == "error"
    assert _CALLS == []
    out = run_for_unit(_TWO_STEP_YAML, inputs={"x": 1}, registry=registry)
    assert out.verdict.status == "pass"
    assert len(_CALLS) == 2
