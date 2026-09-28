"""Tests for `bricks check-brick` (#51, ops#117 CTO ruling 4).

Covers the Definition of Done from the issue: a good brick (exit 0), one
brick per failing check 1-4 (exit 1, each problem carries a ``fix``), a
brick that cannot import (exit 2), the whole stdlib pack (exit 0), and the
agent path — `bricks new brick` scaffolds something `check-brick` accepts
unedited.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bricks.cli.main import app

runner = CliRunner()

_GOOD_BRICK = '''"""A well-formed test brick."""

from __future__ import annotations

from bricks.core.brick import brick


@brick(
    tags=["test"],
    category="general",
    destructive=False,
    idempotent=True,
    description="Double a number. Returns {result: n * 2}.",
)
def double_it(n: float) -> dict[str, float]:
    """Double n. Returns {result: n * 2}."""
    return {"result": n * 2}
'''

_INCOMPLETE_META_BRICK = '''"""A brick with an incomplete Meta: no destructive kwarg."""

from __future__ import annotations

from bricks.core.brick import brick


@brick(description="Triple a number. Returns {result: n * 3}.")
def triple_it(n: float) -> dict[str, float]:
    """Triple n."""
    return {"result": n * 3}
'''

_UNDECLARED_IO_BRICK = '''"""A brick that touches the outside world without declaring it (I3)."""

from __future__ import annotations

from pathlib import Path

from bricks.core.brick import brick


@brick(description="Write text to a file. Returns {result: path}.", destructive=False)
def write_file(path: str, text: str) -> dict[str, str]:
    """Write text to path on disk — but destructive=False, violating I3."""
    Path(path).write_text(text)
    return {"result": path}
'''

_NAME_CLASH_BRICK = '''"""A brick that shadows the stdlib 'divide' brick name."""

from __future__ import annotations

from bricks.core.brick import brick


@brick(description="Not the real divide. Returns {result: a - b}.", destructive=False, idempotent=True)
def divide(a: float, b: float) -> dict[str, float]:
    """Shadow the stdlib 'divide' brick name (a different function object)."""
    return {"result": a - b}
'''

_BAD_CONTRACT_BRICK = '''"""A brick whose return value breaks the Mission 048 contract."""

from __future__ import annotations

from bricks.core.brick import brick


@brick(description="Returns the wrong shape.", destructive=False, idempotent=True)
def wrong_shape(n: float) -> dict[str, float]:
    """Return a dict missing the 'result' key."""
    return {"not_result": n}
'''

_UNDECORATED_BRICK = '''"""A plain function, never decorated with @brick."""

from __future__ import annotations


def not_a_brick(n: float) -> dict[str, float]:
    """Not registered as a brick."""
    return {"result": n}
'''

_SYNTAX_ERROR_FILE = '''"""A file that fails to import."""

def broken(
'''


def _write(tmp_path: Path, filename: str, content: str) -> Path:
    path = tmp_path / filename
    path.write_text(content)
    return path


class TestCheckBrickGood:
    """DoD 1: one good brick exits 0 with no problems."""

    def test_good_brick_exits_0_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write(tmp_path, "good.py", _GOOD_BRICK)
        result = runner.invoke(app, ["check-brick", "good.py:double_it", "--json"])
        assert result.exit_code == 0, result.output
        doc = json.loads(result.stdout)
        assert doc["ok"] is True
        assert doc["problems"] == []

    def test_good_brick_text_mode_exits_0(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write(tmp_path, "good.py", _GOOD_BRICK)
        result = runner.invoke(app, ["check-brick", "good.py:double_it"])
        assert result.exit_code == 0, result.output
        assert "ok" in result.output.lower()


class TestCheckBrickCheck1Declared:
    """DoD 1: check 1 (loads and is declared with @brick) fails."""

    def test_undecorated_function_exits_1(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write(tmp_path, "undecorated.py", _UNDECORATED_BRICK)
        result = runner.invoke(app, ["check-brick", "undecorated.py:not_a_brick", "--json"])
        assert result.exit_code == 1, result.output
        doc = json.loads(result.stdout)
        assert doc["ok"] is False
        checks = {p["check"] for p in doc["problems"]}
        assert "brick.declared" in checks
        for p in doc["problems"]:
            assert p["fix"], "every problem must carry a non-empty fix string"


class TestCheckBrickCheck2NameClash:
    """DoD 1: check 2 (name clash with an installed brick) fails."""

    def test_name_clash_exits_1(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write(tmp_path, "clash.py", _NAME_CLASH_BRICK)
        result = runner.invoke(app, ["check-brick", "clash.py:divide", "--json"])
        assert result.exit_code == 1, result.output
        doc = json.loads(result.stdout)
        assert doc["ok"] is False
        checks = {p["check"] for p in doc["problems"]}
        assert "name.clash" in checks
        for p in doc["problems"]:
            assert p["fix"], "every problem must carry a non-empty fix string"


class TestCheckBrickCheck3Meta:
    """DoD 1: check 3 (Meta incomplete, or undeclared I/O — I3) fails."""

    def test_incomplete_meta_exits_1(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write(tmp_path, "meta.py", _INCOMPLETE_META_BRICK)
        result = runner.invoke(app, ["check-brick", "meta.py:triple_it", "--json"])
        assert result.exit_code == 1, result.output
        doc = json.loads(result.stdout)
        assert doc["ok"] is False
        checks = {p["check"] for p in doc["problems"]}
        assert "meta.destructive" in checks
        for p in doc["problems"]:
            assert p["fix"], "every problem must carry a non-empty fix string"

    def test_undeclared_io_exits_1(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """I3: a brick that touches the outside world must declare destructive=True."""
        monkeypatch.chdir(tmp_path)
        _write(tmp_path, "io_brick.py", _UNDECLARED_IO_BRICK)
        result = runner.invoke(app, ["check-brick", "io_brick.py:write_file", "--json"])
        assert result.exit_code == 1, result.output
        doc = json.loads(result.stdout)
        assert doc["ok"] is False
        checks = {p["check"] for p in doc["problems"]}
        assert "meta.capability" in checks
        for p in doc["problems"]:
            assert p["fix"], "every problem must carry a non-empty fix string"


class TestCheckBrickCheck4Contract:
    """DoD 1: check 4 (contract: must run and return {"result": ...}) fails."""

    def test_bad_contract_exits_1(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write(tmp_path, "bad.py", _BAD_CONTRACT_BRICK)
        result = runner.invoke(app, ["check-brick", "bad.py:wrong_shape", "--json"])
        assert result.exit_code == 1, result.output
        doc = json.loads(result.stdout)
        assert doc["ok"] is False
        checks = {p["check"] for p in doc["problems"]}
        assert "contract.result_key" in checks
        for p in doc["problems"]:
            assert p["fix"], "every problem must carry a non-empty fix string"


class TestCheckBrickCannotImport:
    """DoD 1: a brick that cannot import exits 2."""

    def test_syntax_error_exits_2(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        _write(tmp_path, "broken.py", _SYNTAX_ERROR_FILE)
        result = runner.invoke(app, ["check-brick", "broken.py:broken", "--json"])
        assert result.exit_code == 2, result.output
        doc = json.loads(result.stdout)
        assert doc["ok"] is False
        assert doc["problems"] == []

    def test_missing_file_exits_2(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["check-brick", "nope.py:whatever", "--json"])
        assert result.exit_code == 2, result.output

    def test_missing_file_text_mode_prints_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["check-brick", "nope.py:whatever"])
        assert result.exit_code == 2, result.output
        assert "Error" in result.output


class TestCheckBrickPack:
    """DoD 2: the whole stdlib pack reports ok."""

    def test_stdlib_pack_all_ok(self) -> None:
        result = runner.invoke(app, ["check-brick", "bricks.stdlib", "--json"])
        assert result.exit_code == 0, result.output
        doc = json.loads(result.stdout)
        assert doc["ok"] is True
        assert doc["problems"] == []


class TestCheckBrickAgentPath:
    """DoD 3: `bricks new brick` -> `bricks check-brick` exits 0, no edits."""

    def test_new_brick_scaffold_passes_unedited(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        new_result = runner.invoke(app, ["new", "brick", "demo"])
        assert new_result.exit_code == 0, new_result.output

        scaffold_path = tmp_path / "bricks_lib" / "demo.py"
        before = scaffold_path.read_text()

        check_result = runner.invoke(app, ["check-brick", "bricks_lib/demo.py:demo", "--json"])
        assert check_result.exit_code == 0, check_result.output
        doc = json.loads(check_result.stdout)
        assert doc["ok"] is True
        assert doc["problems"] == []

        # No edits: the scaffold file is exactly what `new brick` wrote.
        after = scaffold_path.read_text()
        assert after == before
