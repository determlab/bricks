"""ci/check_packaging.py: the built wheel's Requires-Dist against what src/ imports (bricks#25)."""

from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent / "ci" / "check_packaging.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_packaging", _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _project(tmp_path: Path, imports: str, requires: list[str], allow: str = "") -> list[str]:
    """Build a fake src tree and a fake wheel; return the argv that checks them."""
    src = tmp_path / "src" / "pkg"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text(imports + "\n", encoding="utf-8")
    dist = tmp_path / "dist"
    dist.mkdir()
    meta = "Metadata-Version: 2.1\nName: pkg\nVersion: 1.0\n" + "".join(f"Requires-Dist: {r}\n" for r in requires)
    with zipfile.ZipFile(dist / "pkg-1.0-py3-none-any.whl", "w") as wheel:
        wheel.writestr("pkg-1.0.dist-info/METADATA", meta)
    ok_file = tmp_path / "unbounded_ok.txt"
    ok_file.write_text(allow, encoding="utf-8")
    return ["--json", "--dist", str(dist), "--src", str(tmp_path / "src"), "--unbounded-ok", str(ok_file)]


def test_import_missing_from_requires_dist_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    argv = _project(tmp_path, "import os\nimport pluggy\nfrom pydantic import BaseModel", ["pydantic>=2.0,<3"])
    assert _load().main(argv) != 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False
    assert any("pluggy" in p and "dependencies" in p for p in out["problems"])


def test_unbounded_dependency_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    argv = _project(tmp_path, "import pydantic", ["pydantic>=2.0"])
    assert _load().main(argv) != 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False
    assert any("pydantic" in p and "upper bound" in p for p in out["problems"])


def test_clean_package_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    argv = _project(
        tmp_path,
        "import os\nimport pkg\nfrom ruamel.yaml import YAML\nimport pydantic",
        ["pydantic>=2.0,<3", "ruamel.yaml>=0.18,<1", "tzdata>=2024.1; sys_platform == 'win32'"],
        allow="tzdata  # calendar versions\n",
    )
    assert _load().main(argv) == 0
    assert json.loads(capsys.readouterr().out) == {"ok": True, "problems": []}
