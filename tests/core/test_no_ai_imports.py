"""Boundary guard: the deterministic engine must never load the AI layer.

``import bricks`` (and the engine CLI module) must not pull in ``bricks_ai``
or any LLM SDK. Run in a subprocess so modules imported by other tests in
this pytest session can't contaminate ``sys.modules``.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[2] / "src")


def _run_isolated(code: str) -> subprocess.CompletedProcess[str]:
    """Run a Python snippet in a fresh interpreter with src/ on the path."""
    env = {**os.environ, "PYTHONPATH": _SRC}
    return subprocess.run(  # noqa: S603  — fixed argv: this interpreter + a literal snippet
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_import_bricks_loads_no_ai_modules() -> None:
    """``import bricks`` must not load bricks_ai or any LLM SDK."""
    code = (
        "import sys\n"
        "import bricks\n"
        "leaked = sorted(\n"
        "    m for m in sys.modules\n"
        "    if m == 'bricks_ai' or m.startswith('bricks_ai.')\n"
        "    or m in ('litellm', 'anthropic', 'openai')\n"
        ")\n"
        "assert not leaked, f'engine import pulled in AI modules: {leaked}'\n"
    )
    result = _run_isolated(code)
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"


def test_import_engine_cli_loads_no_ai_modules() -> None:
    """Importing the CLI module (not invoking AI commands) stays engine-only."""
    code = (
        "import sys\n"
        "import bricks.cli.main\n"
        "leaked = sorted(\n"
        "    m for m in sys.modules\n"
        "    if m == 'bricks_ai' or m.startswith('bricks_ai.')\n"
        ")\n"
        "assert not leaked, f'CLI import pulled in AI modules: {leaked}'\n"
    )
    result = _run_isolated(code)
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"


def test_bricks_facade_hint_on_moved_symbol() -> None:
    """``from bricks import Bricks`` gives a migration hint to bricks_ai."""
    code = (
        "try:\n"
        "    from bricks import Bricks\n"
        "except ImportError as exc:\n"
        "    assert 'bricks_ai' in str(exc), str(exc)\n"
        "else:\n"
        "    raise AssertionError('expected ImportError with migration hint')\n"
    )
    result = _run_isolated(code)
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
