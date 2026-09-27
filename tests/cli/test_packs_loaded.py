"""The CLI registry is the Python API's default registry, plus the config's paths (#39).

Each test runs the real ``bricks`` CLI in a fresh interpreter, from a clean
temp directory, so nothing from this pytest session (imported modules, the
repo as cwd, a stray ``bricks.config.yaml``) can make the stdlib appear.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from bricks import run_blueprint

_REPO_BLUEPRINT = Path(__file__).resolve().parents[2] / "blueprints" / "crm_pipeline.yaml"

_CRM_JSON = json.dumps(
    [
        {"name": "Acme", "status": "active", "monthly_revenue": 4200},
        {"name": "Globex", "status": "churned", "monthly_revenue": 1800},
        {"name": "Initech", "status": "active", "monthly_revenue": 3100},
    ]
)


def _bricks(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the ``bricks`` CLI in a fresh interpreter with *cwd* as the working directory."""
    return subprocess.run(  # noqa: S603  — fixed argv: this interpreter + a literal snippet + test args
        [sys.executable, "-c", "from bricks.cli.main import app; app(prog_name='bricks')", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _clean_dir_with_blueprint(tmp_path: Path) -> Path:
    """A directory with no bricks.config.yaml and a copy of blueprints/crm_pipeline.yaml."""
    work = tmp_path / "clean"
    (work / "blueprints").mkdir(parents=True)
    shutil.copy(_REPO_BLUEPRINT, work / "blueprints" / "crm_pipeline.yaml")
    assert not (work / "bricks.config.yaml").exists()
    return work


def test_list_shows_stdlib_without_config(tmp_path: Path) -> None:
    work = _clean_dir_with_blueprint(tmp_path)
    result = _bricks(work, "list")
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    for name in ("extract_json_from_str", "filter_dict_list", "reduce_sum", "divide"):
        assert f"  {name}" in result.stdout, f"Expected stdlib brick {name!r} in:\n{result.stdout}"


def test_check_passes_without_config(tmp_path: Path) -> None:
    work = _clean_dir_with_blueprint(tmp_path)
    result = _bricks(work, "check", "blueprints/crm_pipeline.yaml")
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    assert "valid: blueprints" in result.stdout, result.stdout


def test_dry_run_passes_without_config(tmp_path: Path) -> None:
    work = _clean_dir_with_blueprint(tmp_path)
    result = _bricks(work, "dry-run", "blueprints/crm_pipeline.yaml")
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"


def test_run_matches_python_api(tmp_path: Path) -> None:
    work = _clean_dir_with_blueprint(tmp_path)
    result = _bricks(work, "run", "blueprints/crm_pipeline.yaml", "-i", f"crm_json={_CRM_JSON}")
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"

    api = run_blueprint(_REPO_BLUEPRINT, inputs={"crm_json": _CRM_JSON})
    assert api.outputs == {"active_count": 2, "total_active_revenue": 7300, "avg_active_revenue": 3650.0}
    for k, v in api.outputs.items():
        assert f"  {k}: {v!r}" in result.stdout, f"Expected {k}={v!r} in:\n{result.stdout}"


def test_init_config_still_finds_stdlib(tmp_path: Path) -> None:
    work = _clean_dir_with_blueprint(tmp_path)
    init = _bricks(work, "init")
    assert init.returncode == 0, f"stdout={init.stdout}\nstderr={init.stderr}"
    assert "paths: []" in (work / "bricks.config.yaml").read_text()
    result = _bricks(work, "check", "blueprints/crm_pipeline.yaml")
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"


def test_config_path_adds_on_top_of_stdlib(tmp_path: Path) -> None:
    work = _clean_dir_with_blueprint(tmp_path)
    (work / "bricks_lib").mkdir()
    (work / "bricks_lib" / "mine.py").write_text(
        "from bricks.core import brick\n\n"
        "@brick(description='A local brick')\n"
        "def my_local_brick(a: int) -> dict[str, int]:\n"
        "    return {'result': a}\n"
        "\n"
        "@brick(description='A local brick that reuses a stdlib name')\n"
        "def divide(a: float, b: float) -> dict[str, float]:\n"
        "    return {'result': -1.0}\n"
    )
    (work / "bricks.config.yaml").write_text("registry:\n  auto_discover: true\n  paths:\n    - 'bricks_lib/'\n")

    listed = _bricks(work, "list")
    assert listed.returncode == 0, f"stdout={listed.stdout}\nstderr={listed.stderr}"
    assert "  my_local_brick" in listed.stdout, listed.stdout
    assert "  extract_json_from_str" in listed.stdout, listed.stdout

    # On a name clash the installed pack wins (the warning is tested below).
    ran = _bricks(work, "run", "blueprints/crm_pipeline.yaml", "-i", f"crm_json={_CRM_JSON}")
    assert ran.returncode == 0, f"stdout={ran.stdout}\nstderr={ran.stderr}"
    assert "  avg_active_revenue: 3650.0" in ran.stdout, ran.stdout


def test_shadowed_local_brick_warns(tmp_path: Path) -> None:
    """A local brick named like a pack brick is not dropped silently (#39)."""
    work = _clean_dir_with_blueprint(tmp_path)
    (work / "lib").mkdir()
    (work / "lib" / "mine.py").write_text(
        "from bricks.core import brick\n\n"
        "@brick()\n"
        "def divide(a: float, b: float) -> dict[str, float]:\n"
        "    return {'result': -1.0}\n"
        "\n"
        "@brick()\n"
        "def my_local_brick(a: int) -> dict[str, int]:\n"
        "    return {'result': a}\n"
    )
    (work / "bricks.config.yaml").write_text("registry:\n  auto_discover: true\n  paths:\n    - 'lib/'\n")

    result = _bricks(work, "run", "blueprints/crm_pipeline.yaml", "-i", f"crm_json={_CRM_JSON}")
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    assert "  avg_active_revenue: 3650.0" in result.stdout, result.stdout
    assert "Warning: local brick 'divide'" in result.stderr, result.stderr
    assert "the pack version wins" in result.stderr, result.stderr
    assert "my_local_brick" not in result.stderr, result.stderr
    assert "Warning" not in result.stdout, result.stdout

    listed = _bricks(work, "list")
    assert "  my_local_brick" in listed.stdout, listed.stdout
