"""Docs are tests (bricks#105).

Every ``bash``/``sh`` command on the first screen of README.md (``## Why Bricks?``,
``## Install`` and every ``## Quick Start`` section) and every ``bash``/``sh``
command in AGENTS.md is extracted and run as written, in a fresh venv. The
extraction and execution are ``dev/quickstart/run_readme.py``'s — this file adds
no second mechanism, only the venv/session plumbing a real end-to-end run needs.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_readme", ROOT / "dev" / "quickstart" / "run_readme.py")
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["run_readme"] = mod  # dataclasses look the module up while building the classes
    spec.loader.exec_module(mod)
    return mod


rr = _load()


def _real_commands():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    return rr.doc_commands(rr.first_screen(readme), "README.md") + rr.doc_commands(agents, "AGENTS.md")


def test_real_docs_have_commands_on_both_files() -> None:
    commands = _real_commands()
    assert any(c.file == "README.md" for c in commands)
    assert any(c.file == "AGENTS.md" for c in commands)


# ---------------------------------------------------------------------------
# The skip cap (bricks#105): a `doc-test: skip` or, with RC_WHEELS unset, a
# `doc-test: main-only` command is a visible skip, and there can be at most
# MAX_DOC_TEST_SKIPS of them so the count cannot grow silently.
# ---------------------------------------------------------------------------


def test_doc_test_skip_count_is_capped() -> None:
    resolved = rr.resolve_doc_commands(_real_commands(), os.environ.get("RC_WHEELS"))
    skipped = [c for c in resolved if c.skipped]
    assert len(skipped) <= rr.MAX_DOC_TEST_SKIPS, [f"{c.file}:{c.line}: {c.skipped}" for c in skipped]


# ---------------------------------------------------------------------------
# A deliberate failure: a bad command must fail naming its block and line.
# ---------------------------------------------------------------------------


def test_a_bad_install_line_fails_with_its_block_and_line_number(tmp_path: Path) -> None:
    text = "# Title\n\n## Install\n\nRun this:\n\n```bash\npip install nonexistent-pkg-xyz\n```\n"
    (cmd,) = rr.doc_commands(text, "README.md")
    assert cmd.line == 8
    (resolved,) = rr.resolve_doc_commands([cmd], None)
    runner = rr.DocRunner(bash=rr.find_bash(), env=dict(os.environ), cwd=tmp_path)
    with pytest.raises(rr.StepFailedError) as excinfo:
        runner.run(resolved)
    assert "README.md:8: `pip install nonexistent-pkg-xyz`" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Mutation check: a corrupted copy of a real command turns red with file:line.
# ---------------------------------------------------------------------------


def test_a_corrupted_command_fails_with_its_file_and_line_number(tmp_path: Path) -> None:
    real = next(c for c in _real_commands() if c.file == "AGENTS.md" and c.expected)
    mutated = real.command.replace("crm_pipeline", "crm_pipelineXXX")
    assert mutated != real.command, "nothing to mutate: the real command changed shape"
    text = f"# Title\n\n```bash\n{mutated}\n```\n\n```\n{(real.expected or [''])[0]}\n```\n"
    (cmd,) = rr.doc_commands(text, "AGENTS.md")
    assert cmd.line == 4
    (resolved,) = rr.resolve_doc_commands([cmd], None)
    runner = rr.DocRunner(bash=rr.find_bash(), env=dict(os.environ), cwd=tmp_path)
    with pytest.raises(rr.StepFailedError) as excinfo:
        runner.run(resolved)
    assert f"AGENTS.md:4: `{mutated}`" in str(excinfo.value)


# ---------------------------------------------------------------------------
# The real CLI test: every doc command, run end to end in one fresh venv —
# a real `pip install`, a real `bricks` CLI, not a mocked subprocess.
# ---------------------------------------------------------------------------


def _run_session(resolved: list, work: Path, bash: str, env: dict[str, str]) -> dict[tuple[str, int], str | None]:
    """Run one ordered session's commands against a shared cwd; None means it passed."""
    work.mkdir(parents=True, exist_ok=True)
    runner = rr.DocRunner(bash=bash, env=env, cwd=work, repo_root=ROOT)
    results: dict[tuple[str, int], str | None] = {}
    for cmd in resolved:
        key = (cmd.file, cmd.line)
        try:
            runner.run(cmd)
            results[key] = None
        except rr.DocSkipError as e:
            results[key] = f"SKIP:{e}"
        except rr.StepFailedError as e:
            results[key] = f"FAIL:{e}"
    return results


@pytest.fixture(scope="module")
def doc_results() -> dict[tuple[str, int], str | None]:
    """Every real doc command's outcome, computed once: README.md and AGENTS.md are
    each their own `git clone`-to-`pip install`-to-CLI session, like a reader's
    terminal, in a venv shared by both (a second `pip install -e .` just re-points
    the editable install at the second session's clone)."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    rc_wheels = os.environ.get("RC_WHEELS")
    readme_cmds = rr.resolve_doc_commands(rr.doc_commands(rr.first_screen(readme), "README.md"), rc_wheels)
    agents_cmds = rr.resolve_doc_commands(rr.doc_commands(agents, "AGENTS.md"), rc_wheels)

    tmp = Path(tempfile.mkdtemp(prefix="bricks-doctest-"))
    try:
        venv_dir = tmp / "venv"
        subprocess.run(  # noqa: S603 — fixed argv, no shell
            [sys.executable, "-m", "venv", str(venv_dir)], check=True
        )
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        env["VIRTUAL_ENV"] = str(venv_dir)
        env["PATH"] = str(rr.venv_bin(venv_dir)) + os.pathsep + env.get("PATH", "")
        env["PYTHONUNBUFFERED"] = "1"
        bash = rr.find_bash()

        results = _run_session(readme_cmds, tmp / "readme", bash, env)
        results.update(_run_session(agents_cmds, tmp / "agents", bash, env))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return results


def _case_ids() -> list[tuple[str, int]]:
    return sorted({(c.file, c.line) for c in _real_commands()})


@pytest.mark.parametrize("key", _case_ids(), ids=[f"{file}:{line}" for file, line in _case_ids()])
def test_doc_command(key: tuple[str, int], doc_results: dict[tuple[str, int], str | None]) -> None:
    outcome = doc_results[key]
    if outcome is None:
        return
    kind, _, detail = outcome.partition(":")
    if kind == "SKIP":
        pytest.skip(detail)
    pytest.fail(detail)
