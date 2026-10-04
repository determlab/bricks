"""``--json`` on ``bricks run``, ``check`` and ``list`` (#40).

With ``--json`` a command writes exactly one JSON document to stdout, for
success and for failure, with the same exit code as without it. Without the
flag the output is byte-for-byte what it was before #40: the expected strings
below were captured from the CLI before the flag existed. ``bricks list`` is
checked on a fixed two-brick registry, so the test pins the format and not
the stdlib's descriptions.

Most tests run the real CLI in a fresh interpreter from a clean temp
directory, the same way as ``test_packs_loaded.py``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from bricks.cli.main import app
from bricks.core.brick import brick
from bricks.core.registry import BrickRegistry
from bricks.errors import BricksConfigError

_REPO_BLUEPRINT = Path(__file__).resolve().parents[2] / "blueprints" / "crm_pipeline.yaml"

_CRM_JSON = json.dumps(
    [
        {"name": "Acme", "status": "active", "monthly_revenue": 4200},
        {"name": "Globex", "status": "churned", "monthly_revenue": 1800},
        {"name": "Initech", "status": "active", "monthly_revenue": 3100},
    ]
)

_BAD_BLUEPRINT = "name: x\nsteps:\n  - name: s\n    brick: nope\n    params: {}\n"


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
    """A directory with no bricks.config.yaml, the CRM blueprint and a blueprint naming an unknown brick."""
    d = tmp_path / "clean"
    (d / "blueprints").mkdir(parents=True)
    shutil.copy(_REPO_BLUEPRINT, d / "blueprints" / "crm_pipeline.yaml")
    (d / "bad.yaml").write_text(_BAD_BLUEPRINT, encoding="utf-8")
    return d


# --- bricks run ------------------------------------------------------------


def test_run_json_success(work: Path) -> None:
    result = _bricks(work, "run", "blueprints/crm_pipeline.yaml", "-i", f"crm_json={_CRM_JSON}", "--json")
    assert result.returncode == 0, result.stderr
    assert _one_json(result) == {
        "ok": True,
        "blueprint": "crm_pipeline",
        "unit": "bench",
        "verdict": "pass",
        "measurements": [],
        "outputs": {"active_count": 2, "total_active_revenue": 7300, "avg_active_revenue": 3650.0},
    }


def test_run_json_step_failure_names_step_and_brick(work: Path) -> None:
    result = _bricks(work, "run", "blueprints/crm_pipeline.yaml", "-i", "crm_json=[]", "--json")
    assert result.returncode == 3
    doc = _one_json(result)
    assert doc["ok"] is False
    assert doc["error"]["type"] == "BrickExecutionError"
    assert doc["error"]["step"] == "avg_revenue"
    assert doc["error"]["brick"] == "divide"
    assert doc["error"]["message"] == ("Brick 'divide' failed at step 'avg_revenue': Division by zero: b must not be 0")
    # #49: any other BrickError ending the run is verdict "error", ok stays false.
    assert doc["unit"] == "bench"
    assert doc["verdict"] == "error"


@pytest.mark.parametrize(
    ("args", "error_type", "reaches_engine"),
    [
        (["missing.yaml"], "FileNotFoundError", False),
        (["blueprints/crm_pipeline.yaml", "-i", "novalue"], "InvalidInputError", False),
        (["bad.yaml"], "BrickNotFoundError", True),
    ],
)
def test_run_json_other_failures(work: Path, args: list[str], error_type: str, reaches_engine: bool) -> None:
    result = _bricks(work, "run", *args, "--json")
    # verdict "error" (the run was attempted and broke) exits 3; earlier failures exit 1.
    assert result.returncode == (3 if reaches_engine else 1)
    doc = _one_json(result)
    assert doc["ok"] is False
    assert doc["error"]["type"] == error_type
    assert doc["error"]["message"]
    assert "step" not in doc["error"]
    # "unit"/"verdict" only make sense once a run was attempted (bad.yaml fails
    # inside engine.run() on the unknown brick); a failure before that — a
    # missing file or a bad -i — never touches the engine.
    if reaches_engine:
        assert doc["unit"] == "bench"
        assert doc["verdict"] == "error"
    else:
        assert "unit" not in doc
        assert "verdict" not in doc


def test_run_json_yaml_error(work: Path) -> None:
    (work / "broken.yaml").write_text("name: [unclosed\n", encoding="utf-8")
    result = _bricks(work, "run", "broken.yaml", "--json")
    assert result.returncode == 1
    doc = _one_json(result)
    assert doc["ok"] is False
    assert doc["error"]["type"] == "YamlLoadError"


def test_run_json_non_serialisable_outputs_fall_back_to_str(work: Path) -> None:
    """A value that is not a JSON type is written as str(value); tuples become lists."""
    (work / "lib").mkdir()
    (work / "lib" / "odd.py").write_text(
        "import datetime\n"
        "from bricks.core import brick\n\n"
        "@brick()\n"
        "def odd_values(x: int) -> dict[str, object]:\n"
        "    return {'day': datetime.date(2026, 1, 2), 'nan': float('nan'), 'pair': (1, 'a'),\n"
        "            'nested': {'when': datetime.date(2026, 1, 3), 'n': 1}}\n",
        encoding="utf-8",
    )
    (work / "bricks.config.yaml").write_text(
        "registry:\n  auto_discover: true\n  paths:\n    - 'lib/'\n", encoding="utf-8"
    )
    (work / "odd.yaml").write_text(
        "name: odd\n"
        "steps:\n"
        "  - name: s\n"
        "    brick: odd_values\n"
        "    params: {x: 1}\n"
        "    save_as: r\n"
        "outputs_map:\n"
        '  day: "${r.day}"\n'
        '  nan: "${r.nan}"\n'
        '  pair: "${r.pair}"\n'
        '  nested: "${r.nested}"\n',
        encoding="utf-8",
    )
    result = _bricks(work, "run", "odd.yaml", "--json")
    assert result.returncode == 0, result.stderr
    assert "NaN" not in result.stdout  # strict JSON: no bare NaN token
    assert _one_json(result)["outputs"] == {
        "day": "2026-01-02",
        "nan": "nan",
        "pair": [1, "a"],
        "nested": {"when": "2026-01-03", "n": 1},
    }


def test_run_human_output_unchanged(work: Path) -> None:
    """Byte-for-byte as before #40, plus the "Verdict: ..." line #49 adds."""
    ok = _bricks(work, "run", "blueprints/crm_pipeline.yaml", "-i", f"crm_json={_CRM_JSON}")
    assert (ok.returncode, ok.stdout, ok.stderr) == (
        0,
        "Blueprint 'crm_pipeline' completed.\nOutputs:\n"
        "  active_count: 2\n  total_active_revenue: 7300\n  avg_active_revenue: 3650.0\n"
        "Verdict: PASS (unit bench)\n",
        "",
    )
    failed = _bricks(work, "run", "blueprints/crm_pipeline.yaml", "-i", "crm_json=[]")
    assert (failed.returncode, failed.stdout, failed.stderr) == (
        3,
        "",
        "Execution error: Brick 'divide' failed at step 'avg_revenue': Division by zero: b must not be 0\n"
        "Verdict: ERROR (unit bench): "
        "Brick 'divide' failed at step 'avg_revenue': Division by zero: b must not be 0\n",
    )
    missing = _bricks(work, "run", "missing.yaml")
    assert (missing.returncode, missing.stdout, missing.stderr) == (
        1,
        "",
        "Error: Blueprint file not found: missing.yaml\n",
    )


def test_run_json_keeps_clash_warning_on_stderr(work: Path) -> None:
    (work / "lib").mkdir()
    (work / "lib" / "mine.py").write_text(
        "from bricks.core import brick\n\n"
        "@brick()\n"
        "def divide(a: float, b: float) -> dict[str, float]:\n"
        "    return {'result': -1.0}\n",
        encoding="utf-8",
    )
    (work / "bricks.config.yaml").write_text(
        "registry:\n  auto_discover: true\n  paths:\n    - 'lib/'\n", encoding="utf-8"
    )
    result = _bricks(work, "run", "blueprints/crm_pipeline.yaml", "-i", f"crm_json={_CRM_JSON}", "--json")
    assert result.returncode == 0, result.stderr
    assert _one_json(result)["ok"] is True
    assert "Warning: local brick 'divide'" in result.stderr


# --- bricks check ----------------------------------------------------------


def test_check_json_valid(work: Path) -> None:
    result = _bricks(work, "check", "blueprints/crm_pipeline.yaml", "--json")
    assert result.returncode == 0, result.stderr
    assert _one_json(result) == {"ok": True, "file": "blueprints/crm_pipeline.yaml", "errors": []}


def test_check_json_invalid(work: Path) -> None:
    result = _bricks(work, "check", "bad.yaml", "--json")
    assert result.returncode == 1
    assert _one_json(result) == {
        "ok": False,
        "file": "bad.yaml",
        "errors": ["Step 's': brick 'nope' not found in registry"],
    }


def test_check_json_missing_file(work: Path) -> None:
    result = _bricks(work, "check", "missing.yaml", "--json")
    assert result.returncode == 1
    assert _one_json(result) == {"ok": False, "file": "missing.yaml", "errors": ["File not found: missing.yaml"]}


def test_check_json_yaml_error(work: Path) -> None:
    (work / "broken.yaml").write_text("name: [unclosed\n", encoding="utf-8")
    result = _bricks(work, "check", "broken.yaml", "--json")
    assert result.returncode == 1
    doc = _one_json(result)
    assert doc["ok"] is False
    assert doc["file"] == "broken.yaml"
    assert len(doc["errors"]) == 1
    assert doc["errors"][0].startswith("Error loading YAML: ")


def test_check_human_output_unchanged(work: Path) -> None:
    ok = _bricks(work, "check", "blueprints/crm_pipeline.yaml")
    assert (ok.returncode, ok.stdout, ok.stderr) == (0, f"valid: {Path('blueprints/crm_pipeline.yaml')}\n", "")
    bad = _bricks(work, "check", "bad.yaml")
    assert (bad.returncode, bad.stdout, bad.stderr) == (
        1,
        "",
        "Validation errors in bad.yaml:\n  - Step 's': brick 'nope' not found in registry\n",
    )
    missing = _bricks(work, "check", "missing.yaml")
    assert (missing.returncode, missing.stdout, missing.stderr) == (1, "", "Error: File not found: missing.yaml\n")


# --- bricks list -----------------------------------------------------------


def test_list_json(work: Path) -> None:
    result = _bricks(work, "list", "--json")
    assert result.returncode == 0, result.stderr
    doc = _one_json(result)
    assert doc["ok"] is True
    bricks = doc["bricks"]
    assert len(bricks) == 104
    by_name = {b["name"]: b for b in bricks}
    entry = by_name["absolute_value"]
    # output_keys is whatever bricks.core.schema.brick_schema reports (empty for
    # a brick annotated `-> dict[str, float]`); the test checks only its type.
    assert isinstance(entry.pop("output_keys"), list)
    assert entry == {
        "name": "absolute_value",
        "description": "Return the absolute value of a number. Returns {result: absolute}.",
        "tags": ["math", "arithmetic"],
        "category": "math",
        "destructive": False,
        "idempotent": True,
        "input_keys": ["value"],
    }
    for b in bricks:
        assert "\n" not in b["description"], b["name"]


def _two_bricks() -> BrickRegistry:
    """A fixed registry, so the list format is tested without the stdlib's content."""

    @brick(tags=["math", "demo"], description="Add two numbers.\n\n    Returns {result: sum}.")
    def add(a: float, b: float) -> dict[str, float]:
        return {"result": a + b}

    @brick(destructive=True)
    def wipe(path: str) -> dict[str, bool]:
        return {"done": True}

    reg = BrickRegistry()
    for fn in (add, wipe):
        reg.register(fn.__name__, fn, fn.__brick_meta__)  # type: ignore[attr-defined]
    return reg


def test_list_human_output_format_unchanged(work: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The text format of ``bricks list`` as it was before #40, on a fixed two-brick registry."""
    monkeypatch.chdir(work)
    monkeypatch.setattr("bricks.cli.main.build_default_registry", _two_bricks)
    result = CliRunner().invoke(app, ["list"])
    assert result.exit_code == 0
    assert result.stdout == (
        "Registered bricks (2):\n"
        "  add [math, demo] - Add two numbers.\n"
        "\n"
        "    Returns {result: sum}.\n"
        "  wipe [DESTRUCTIVE]\n"
    )

    as_json = CliRunner().invoke(app, ["list", "--json"])
    assert as_json.exit_code == 0
    assert [(b["name"], b["description"], b["destructive"]) for b in json.loads(as_json.stdout)["bricks"]] == [
        ("add", "Add two numbers.", False),
        ("wipe", "", True),
    ]


# --- a brick that prints ---------------------------------------------------


def test_json_stdout_is_json_alone_when_a_brick_prints(work: Path) -> None:
    """A local brick that prints at import and at run time: the text goes to stderr."""
    (work / "lib").mkdir()
    (work / "lib" / "noisy.py").write_text(
        "from bricks.core import brick\n\n"
        "print('noisy: imported')\n\n"
        "@brick()\n"
        "def noisy(x: int) -> dict[str, int]:\n"
        "    print('noisy: running')\n"
        "    return {'result': x}\n",
        encoding="utf-8",
    )
    (work / "bricks.config.yaml").write_text(
        "registry:\n  auto_discover: true\n  paths:\n    - 'lib/'\n", encoding="utf-8"
    )
    (work / "noisy.yaml").write_text(
        "name: noisy\n"
        "steps:\n"
        "  - name: s\n"
        "    brick: noisy\n"
        "    params: {x: 7}\n"
        "    save_as: r\n"
        "outputs_map:\n"
        '  result: "${r.result}"\n',
        encoding="utf-8",
    )

    ran = _bricks(work, "run", "noisy.yaml", "--json")
    assert ran.returncode == 0, ran.stderr
    assert _one_json(ran) == {
        "ok": True,
        "blueprint": "noisy",
        "unit": "bench",
        "verdict": "pass",
        "measurements": [],
        "outputs": {"result": 7},
    }
    assert "noisy: imported" in ran.stderr
    assert "noisy: running" in ran.stderr

    checked = _bricks(work, "check", "noisy.yaml", "--json")
    assert checked.returncode == 0, checked.stderr
    assert _one_json(checked) == {"ok": True, "file": "noisy.yaml", "errors": []}
    assert "noisy: imported" in checked.stderr

    listed = _bricks(work, "list", "--json")
    assert listed.returncode == 0, listed.stderr
    assert "noisy" in {b["name"] for b in _one_json(listed)["bricks"]}
    assert "noisy: imported" in listed.stderr


# --- a bricks.config.yaml that cannot be read ------------------------------


@pytest.mark.parametrize(
    "config",
    [
        "registry: [not, a, mapping\n",  # not YAML
        "registry:\n  auto_discover: {not: a bool}\n",  # YAML, but fails the config model
    ],
)
def test_json_when_config_is_broken(work: Path, config: str) -> None:
    (work / "bricks.config.yaml").write_text(config, encoding="utf-8")
    for args in (["run", "blueprints/crm_pipeline.yaml"], ["list"]):
        result = _bricks(work, *args, "--json")
        assert result.returncode == 1
        doc = _one_json(result)
        assert doc["ok"] is False
        assert doc["error"]["type"] == "ConfigError"
        assert doc["error"]["message"]
    checked = _bricks(work, "check", "blueprints/crm_pipeline.yaml", "--json")
    assert checked.returncode == 1
    doc = _one_json(checked)
    assert doc["ok"] is False
    assert len(doc["errors"]) == 1


# --- a registry that cannot be built ---------------------------------------


def _no_packs() -> Any:
    raise BricksConfigError("No brick packs are installed.")


_NO_PACKS = {"type": "BricksConfigError", "message": "No brick packs are installed."}


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (["list", "--json"], {"ok": False, "error": _NO_PACKS}),
        (["run", "blueprints/crm_pipeline.yaml", "--json"], {"ok": False, "error": _NO_PACKS}),
        (
            ["check", "blueprints/crm_pipeline.yaml", "--json"],
            {"ok": False, "file": "blueprints/crm_pipeline.yaml", "errors": ["No brick packs are installed."]},
        ),
    ],
)
def test_json_when_registry_cannot_be_built(
    work: Path, monkeypatch: pytest.MonkeyPatch, args: list[str], expected: dict[str, Any]
) -> None:
    monkeypatch.chdir(work)
    monkeypatch.setattr("bricks.cli.main.build_default_registry", _no_packs)
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 1
    assert json.loads(result.stdout) == expected
