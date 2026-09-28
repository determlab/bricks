"""``bricks run``: a pass/fail/error verdict and ``--unit`` (#49).

Record.md §2: the verdict is derived, never set by hand. ``verdict = fail`` if
any ``measure`` step returned ``pass: false``, or a guard failed
(``GuardFailedError``); ``verdict = error`` if any other ``BrickError`` ended
the run; else ``verdict = pass``. Exit code is 0 on pass, 1 on fail or error.
``--unit`` defaults to ``"bench"`` and is never blank.

Runs the real CLI in a fresh interpreter from a clean temp directory, the same
way as ``test_json_output.py``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

# A measurement blueprint: one `measure` step against 4.9-5.1V limits — the
# exact shape the issue's --json example ("psu_limits") uses.
_PSU_LIMITS_YAML = """\
name: psu_limits
description: "Measure vout against 4.9-5.1V limits."
inputs:
  vout: "number"
steps:
  - name: vout
    brick: measure
    params:
      name: vout
      value: "${vout}"
      unit: "V"
      min: 4.9
      max: 5.1
    save_as: vout_result
outputs_map:
  vout: "${vout_result.result}"
"""

# A guard that fails when `threshold` is not greater than 3.
_GUARDED_YAML = """\
name: guarded
description: "A guard that stops a bad unit."
inputs:
  threshold: "number"
steps:
  - name: enough
    type: guard
    brick: compare_values
    params:
      a: "${threshold}"
      b: 3
      operator: gt
    message: "threshold too low"
outputs_map: {}
"""

# A plain brick error (not a guard, not an unknown brick): division by zero.
_DIVIDER_YAML = """\
name: divider
description: "Divide a by b; raises when b is 0."
inputs:
  a: "number"
  b: "number"
steps:
  - name: div
    brick: divide
    params:
      a: "${a}"
      b: "${b}"
    save_as: r
outputs_map:
  result: "${r.result}"
"""


def _bricks(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the ``bricks`` CLI in a fresh interpreter, stdout and stderr decoded as UTF-8."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(  # noqa: S603  — fixed argv: this interpreter + a literal snippet + test args
        [sys.executable, "-c", "from bricks.cli.main import app; app(prog_name='bricks')", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )


def _one_json(result: subprocess.CompletedProcess[str]) -> Any:
    """Parse stdout as exactly one JSON document (json.loads rejects anything extra)."""
    return json.loads(result.stdout)


@pytest.fixture
def work(tmp_path: Path) -> Path:
    """A clean directory with the three test blueprints, no bricks.config.yaml."""
    (tmp_path / "psu_limits.yaml").write_text(_PSU_LIMITS_YAML)
    (tmp_path / "guarded.yaml").write_text(_GUARDED_YAML)
    (tmp_path / "divider.yaml").write_text(_DIVIDER_YAML)
    return tmp_path


# --- pass -------------------------------------------------------------------


def test_pass_json_default_unit_is_bench(work: Path) -> None:
    result = _bricks(work, "run", "psu_limits.yaml", "-i", "vout=4.98", "--json")
    assert result.returncode == 0, result.stderr
    row = {"name": "vout", "value": 4.98, "unit": "V", "limits": {"min": 4.9, "max": 5.1}, "pass": True}
    assert _one_json(result) == {
        "ok": True,
        "blueprint": "psu_limits",
        "unit": "bench",
        "verdict": "pass",
        "measurements": [{"step": "vout", **row}],
        "outputs": {"vout": row},
    }


def test_pass_text_prints_verdict_line(work: Path) -> None:
    result = _bricks(work, "run", "psu_limits.yaml", "-i", "vout=4.98")
    assert result.returncode == 0, result.stderr
    assert result.stdout.endswith("Verdict: PASS (unit bench)\n")


# --- fail: a measure step out of bounds --------------------------------------


def test_measure_fail_json(work: Path) -> None:
    result = _bricks(work, "run", "psu_limits.yaml", "-i", "vout=4.7", "--unit", "SN-2", "--json")
    assert result.returncode == 1
    row = {"name": "vout", "value": 4.7, "unit": "V", "limits": {"min": 4.9, "max": 5.1}, "pass": False}
    assert _one_json(result) == {
        "ok": True,
        "blueprint": "psu_limits",
        "unit": "SN-2",
        "verdict": "fail",
        "measurements": [{"step": "vout", **row}],
        "outputs": {"vout": row},
    }


def test_measure_fail_text_matches_issue_example(work: Path) -> None:
    """The exact line the issue specifies: `Verdict: FAIL (unit SN-2): vout 4.7 V not in [4.9, 5.1]`."""
    result = _bricks(work, "run", "psu_limits.yaml", "-i", "vout=4.7", "--unit", "SN-2")
    assert result.returncode == 1
    assert "Verdict: FAIL (unit SN-2): vout 4.7 V not in [4.9, 5.1]" in result.stdout


# --- fail: a guard ------------------------------------------------------------


def test_guard_fail_json_is_ok_true_verdict_fail(work: Path) -> None:
    """A guard fail is `ok: true` — the run did what it should: it stopped a bad unit."""
    result = _bricks(work, "run", "guarded.yaml", "-i", "threshold=1", "--unit", "SN-9", "--json")
    assert result.returncode == 1
    assert _one_json(result) == {
        "ok": True,
        "blueprint": "guarded",
        "unit": "SN-9",
        "verdict": "fail",
        "measurements": [],
        "outputs": {},
    }


def test_guard_pass_json(work: Path) -> None:
    result = _bricks(work, "run", "guarded.yaml", "-i", "threshold=5", "--json")
    assert result.returncode == 0, result.stderr
    doc = _one_json(result)
    assert doc["ok"] is True
    assert doc["verdict"] == "pass"


def test_guard_fail_text_prints_verdict_line(work: Path) -> None:
    result = _bricks(work, "run", "guarded.yaml", "-i", "threshold=1", "--unit", "SN-9")
    assert result.returncode == 1
    assert "Verdict: FAIL (unit SN-9):" in result.stdout
    assert "threshold too low" in result.stdout


# --- error: any other BrickError ---------------------------------------------


def test_brick_error_json_keeps_ok_false_and_adds_verdict_error(work: Path) -> None:
    result = _bricks(work, "run", "divider.yaml", "-i", "a=1", "-i", "b=0", "--unit", "SN-3", "--json")
    assert result.returncode == 1
    doc = _one_json(result)
    assert doc["ok"] is False
    assert doc["unit"] == "SN-3"
    assert doc["verdict"] == "error"
    assert doc["error"]["type"] == "BrickExecutionError"
    assert doc["error"]["step"] == "div"
    assert doc["error"]["brick"] == "divide"


def test_brick_error_text_prints_verdict_line(work: Path) -> None:
    result = _bricks(work, "run", "divider.yaml", "-i", "a=1", "-i", "b=0", "--unit", "SN-3")
    assert result.returncode == 1
    assert "Verdict: ERROR (unit SN-3):" in result.stdout


# --- --unit is never blank ----------------------------------------------------


def test_unit_blank_falls_back_to_bench(work: Path) -> None:
    result = _bricks(work, "run", "psu_limits.yaml", "-i", "vout=4.98", "--unit", "", "--json")
    assert result.returncode == 0, result.stderr
    assert _one_json(result)["unit"] == "bench"


# --- the same blueprint run twice with two different units -------------------


def test_same_blueprint_two_units_differ_in_unit_and_verdict(work: Path) -> None:
    first = _bricks(work, "run", "psu_limits.yaml", "-i", "vout=4.98", "--unit", "SN-1", "--json")
    second = _bricks(work, "run", "psu_limits.yaml", "-i", "vout=4.7", "--unit", "SN-2", "--json")

    assert first.returncode == 0, first.stderr
    assert second.returncode == 1

    first_doc = _one_json(first)
    second_doc = _one_json(second)

    assert first_doc["unit"] == "SN-1"
    assert second_doc["unit"] == "SN-2"
    assert first_doc["unit"] != second_doc["unit"]

    assert first_doc["verdict"] == "pass"
    assert second_doc["verdict"] == "fail"
    assert first_doc["verdict"] != second_doc["verdict"]
