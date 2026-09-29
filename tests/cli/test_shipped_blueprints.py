"""Every blueprint in ``blueprints/`` is checked and run (#74).

The cases are the glob of ``blueprints/*.yaml``, so a new file adds a case with
no edit to the parametrization. Each file needs one entry in ``_INPUTS``; a
file without one fails with a message that says so.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import bricks

_BLUEPRINTS = Path(__file__).resolve().parents[2] / "blueprints"

_CRM_JSON = json.dumps(
    [
        {"name": "Acme", "status": "active", "monthly_revenue": 4200},
        {"name": "Globex", "status": "churned", "monthly_revenue": 1800},
        {"name": "Initech", "status": "active", "monthly_revenue": 3100},
    ]
)

# One small documented input per shipped file, keyed by file name.
_INPUTS: dict[str, dict[str, Any]] = {
    "crm_hallucination.yaml": {"crm_json": _CRM_JSON},
    "crm_pipeline.yaml": {"crm_json": _CRM_JSON},
    "crm_reuse.yaml": {"crm_json": _CRM_JSON},
    "psu_limits.yaml": {"vout": 5.0, "iout": 0.4, "ripple_pp": 12},
}


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


@pytest.mark.parametrize(
    "path", sorted(_BLUEPRINTS.glob("*.yaml")), ids=lambda p: p.name
)
def test_shipped_blueprint_checks_and_runs(path: Path) -> None:
    assert path.name in _INPUTS, (
        f"blueprints/{path.name} has no input in _INPUTS in "
        "tests/cli/test_shipped_blueprints.py: add one small dict for it"
    )

    checked = _bricks("check", str(path), "--json")
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert json.loads(checked.stdout)["ok"] is True

    outcome = bricks.run_for_unit(path, inputs=_INPUTS[path.name], unit="SN-1")
    assert outcome.verdict.status == "pass", outcome.model_dump_json()
