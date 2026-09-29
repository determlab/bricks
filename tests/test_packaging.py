"""The distribution is named bricks-engine; the import name stays ``bricks``."""

from __future__ import annotations

import re
from pathlib import Path

import bricks


def test_pyproject_name_and_version_match_package() -> None:
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    name = re.search(r'^name = "([^"]+)"', text, re.MULTILINE)
    version = re.search(r'^version = "([^"]+)"', text, re.MULTILINE)
    assert name is not None and version is not None
    assert name.group(1) == "bricks-engine"
    assert bricks.__version__ == version.group(1)
