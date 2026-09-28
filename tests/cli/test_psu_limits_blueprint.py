"""``blueprints/psu_limits.yaml``: the first test blueprint (#50).

Runs the shipped blueprint through the real CLI, one passing unit and one
failing unit, the same two commands AGENTS.md shows.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

BLUEPRINT = Path(__file__).resolve().parents[2] / "blueprints" / "psu_limits.yaml"


def _bricks(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the ``bricks`` CLI in a fresh interpreter, stdout and stderr decoded as UTF-8."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(  # noqa: S603  — fixed argv: this interpreter + a literal snippet + test args
        [sys.executable, "-c", "from bricks.cli.main import app; app(prog_name='bricks')", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )


def _run_json(unit: str, vout: str) -> tuple[int, Any]:
    result = _bricks(
        "run", str(BLUEPRINT), "--unit", unit, "-i", f"vout={vout}", "-i", "iout=0.4", "-i", "ripple_pp=12", "--json"
    )
    return result.returncode, json.loads(result.stdout)


def test_check_is_valid() -> None:
    result = _bricks("check", str(BLUEPRINT), "--json")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["ok"] is True


def test_passing_unit_exits_0_with_verdict_pass() -> None:
    code, doc = _run_json("SN-1", "5.0")
    assert code == 0
    assert doc["verdict"] == "pass"
    assert doc["unit"] == "SN-1"
    assert [m["name"] for m in doc["measurements"]] == ["vout", "iout", "ripple_pp"]
    assert all(m["pass"] for m in doc["measurements"])


def test_failing_unit_exits_1_with_verdict_fail() -> None:
    code, doc = _run_json("SN-2", "4.7")
    assert code == 1
    assert doc["verdict"] == "fail"
    assert doc["unit"] == "SN-2"
    assert [m["name"] for m in doc["measurements"] if not m["pass"]] == ["vout"]


def test_text_mode_last_line_is_the_verdict() -> None:
    ok = _bricks("run", str(BLUEPRINT), "--unit", "SN-1", "-i", "vout=5.0", "-i", "iout=0.4", "-i", "ripple_pp=12")
    assert ok.returncode == 0, ok.stderr
    assert ok.stdout.splitlines()[-1] == "Verdict: PASS (unit SN-1)"
    bad = _bricks("run", str(BLUEPRINT), "--unit", "SN-2", "-i", "vout=4.7", "-i", "iout=0.4", "-i", "ripple_pp=12")
    assert bad.returncode == 1
    assert bad.stdout.splitlines()[-1].startswith("Verdict: FAIL (unit SN-2)")
