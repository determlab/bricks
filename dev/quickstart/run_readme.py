#!/usr/bin/env python
"""Run the README's Quick Start exactly as printed, in a clean venv (bricks#41).

The same check as shal#159, for bricks. The README is the source: this script
keeps no copy of any command. It reads ``README.md`` and runs the fenced blocks
of every ``## Quick Start`` section (up to the next ``## `` heading).

**Which blocks run: a marker, not a guess.** Each fenced block in a Quick Start
section must have, on the nearest non-blank line above its opening fence, one of

    <!-- quickstart: run -->     the block runs, and its shown output is checked
    <!-- quickstart: skip -->    an illustration (e.g. ``inputs={...}``); not run

An unmarked block there fails the run, so a new block cannot slip in untested.
At least one ``python`` and one ``bash`` block must be marked ``run``.

**Shown output.** The README shows output as comment lines, and so does this:

- A ``python`` block runs as one script with the venv's ``python``. The whole-line
  ``#`` comments at its end (after the last code line) are its expected stdout.
- A ``bash`` block runs one command line at a time, with ``bash -c "<line>"``,
  so quoting and a trailing ``# note`` mean what they mean to a reader's shell.
  The whole-line ``#`` comments right under a command (up to a blank line or the
  next command) are that command's expected output.

The leading ``#`` and one space are dropped from each comment line. A ``#`` line
in a ``bash`` run block that is not directly under a command (a blank line in
between) fails the run, and so does a ``~~~`` or indented fence in a Quick Start
section: either would otherwise be skipped without a word. A command or
block with no comment lines under it is checked on its exit code only.

**Pass/fail.** A step fails when it exits non-zero, or when its output (stdout
and stderr together, as a terminal shows them) differs from the shown output.
Lines are compared exactly, ignoring only CRLF and trailing whitespace.

**What "the wheel" means here.** bricks is not on PyPI; the README's Install
section says ``git clone`` then ``pip install -e .``. That section is not run:
``git clone`` would fetch ``main``, not this commit. Instead the wheel built
from this commit is installed into the clean venv (``python -m pip install
<wheel>``, its dependencies from PyPI) — what the planned PyPI release will
serve, and stricter than ``-e .`` because it catches a file the package forgets
to ship. The blocks then run in a fresh temp dir holding a copy of the repo's
``blueprints/`` and nothing else, standing in for the clone the reader ``cd``-ed
into: the Quick Start names ``blueprints/crm_pipeline.yaml``, and no other part
of the checkout (no ``src/``) can leak in.

**Bash on Windows.** The CLI line quotes its JSON with single quotes, which only
a POSIX shell reads as the README means. So the commands always run in bash: on
Windows that is Git Bash (the ``bash`` on ``PATH``, skipping the WSL launchers
in ``System32`` and ``WindowsApps``; else the one next to ``git``). ``--bash``
overrides.

**Time to first success.** Seconds from the start of the wheel's ``pip install``
to the end of the first step that shows output and passed. Printed, and appended
to ``$GITHUB_STEP_SUMMARY`` when that is set.

Usage:
    run_readme.py --venv VENV_DIR --dist DIST_DIR [--readme README.md] [--bash PATH]

``VENV_DIR`` is a clean venv (created by the caller, nothing installed).
``DIST_DIR`` must hold exactly one wheel. Exit 0 when every step passes, 1
otherwise, with the failing step and a diff on stdout.
"""

from __future__ import annotations

import argparse
import contextlib
import difflib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

_SECTION = re.compile(r"^##\s+Quick Start\b")
_FENCE = re.compile(r"^```\s*([\w-]*)\s*$")
# A fence this runner does not read: a tilde fence, or a backtick fence with leading spaces.
_ODD_FENCE = re.compile(r"^(\s+```|\s*~~~)")
_MARKER = re.compile(r"^<!--\s*quickstart:\s*(run|skip)\s*-->$")
RUN_LANGS = {"python", "bash"}


class ReadmeError(Exception):
    """The README's Quick Start cannot be run as printed."""


class StepFailedError(Exception):
    """A Quick Start step failed or printed something other than the README shows."""


@dataclass
class Block:
    lang: str
    text: str
    line: int  # 1-based README line of the opening fence
    marker: str  # "run" or "skip"


@dataclass
class Step:
    kind: str  # "python" (a whole block) or "bash" (one command line)
    source: str
    line: int  # README line of the command (bash) or of the opening fence (python)
    expected: list[str] | None = None


def quickstart_blocks(readme: str) -> list[Block]:
    """Every fenced block of every ``## Quick Start`` section, in order, with its marker."""
    lines = readme.replace("\r\n", "\n").split("\n")
    blocks: list[Block] = []
    in_section = False
    fence: Block | None = None
    body: list[str] = []
    last_text = ""  # nearest non-blank line outside a fence
    sections = 0
    for i, ln in enumerate(lines):
        if fence is not None:
            if ln.strip() == "```":
                fence.text = "\n".join(body)
                blocks.append(fence)
                fence = None
                last_text = ln  # a marker above one block never carries to the next
            else:
                body.append(ln)
            continue
        if ln.startswith("## "):
            in_section = bool(_SECTION.match(ln))
            sections += in_section
        m = _FENCE.match(ln)
        if in_section and not m and _ODD_FENCE.match(ln):
            raise ReadmeError(
                f"README line {i + 1}: a Quick Start code block must open with ``` at the start of the "
                "line (no ~~~, no indent), or this runner would skip it"
            )
        if m and in_section:
            mark = _MARKER.match(last_text.strip())
            if not mark:
                raise ReadmeError(
                    f"README line {i + 1}: a ```{m.group(1)} block in a Quick Start section has no "
                    "`<!-- quickstart: run -->` or `<!-- quickstart: skip -->` marker above it"
                )
            fence = Block(lang=m.group(1).lower(), text="", line=i + 1, marker=mark.group(1))
            body = []
        elif m:  # a fence outside Quick Start: skip over its body
            fence = Block(lang="", text="", line=i + 1, marker="outside")
            body = []
        elif ln.strip():
            last_text = ln
    if fence is not None:
        raise ReadmeError(f"README line {fence.line}: code fence never closed")
    if sections == 0:
        raise ReadmeError("no '## Quick Start' section in the README")
    return [b for b in blocks if b.marker != "outside"]


def _comment(line: str) -> str:
    """A shown-output comment line without its ``#`` and one space."""
    text = line[1:]
    return text[1:] if text.startswith(" ") else text


def plan(blocks: list[Block]) -> list[Step]:
    """Turn the ``run`` blocks into ordered steps, each with the output the README shows."""
    steps: list[Step] = []
    for b in blocks:
        if b.marker == "skip":
            continue
        if b.lang not in RUN_LANGS:
            raise ReadmeError(f"README line {b.line}: don't know how to run a ```{b.lang} block")
        rows = b.text.split("\n")
        if b.lang == "python":
            end = len(rows)
            while end and not rows[end - 1].strip():
                end -= 1
            start = end
            while start and rows[start - 1].startswith("#"):
                start -= 1
            if start == 0:
                raise ReadmeError(f"README line {b.line}: ```python block has no code")
            shown = [_comment(r) for r in rows[start:end]]
            steps.append(Step("python", "\n".join(rows[:start]) + "\n", b.line, shown or None))
            continue
        current: Step | None = None  # the command whose shown output is still being read
        found = False
        for k, row in enumerate(rows):
            line_no = b.line + 1 + k
            if not row.strip():
                current = None
            elif row.startswith("#"):
                if current is None:
                    raise ReadmeError(
                        f"README line {line_no}: a `#` output line must sit directly under its command "
                        "(no blank line between), or it would be silently ignored"
                    )
                current.expected = [*(current.expected or []), _comment(row)]
            else:
                if row.rstrip().endswith("\\"):
                    raise ReadmeError(f"README line {line_no}: a continued command line is not supported")
                current = Step("bash", row.strip(), line_no)
                steps.append(current)
                found = True
        if not found:
            raise ReadmeError(f"README line {b.line}: ```bash block has no command")
    for lang in sorted(RUN_LANGS):
        if not any(s.kind == lang for s in steps):
            raise ReadmeError(f"no ```{lang} block in the Quick Start is marked `<!-- quickstart: run -->`")
    return steps


def _norm(text: list[str] | str) -> list[str]:
    lines = text.replace("\r\n", "\n").split("\n") if isinstance(text, str) else list(text)
    lines = [ln.rstrip() for ln in lines]
    while lines and not lines[-1]:
        lines.pop()
    return lines


def output_matches(expected: list[str], actual: str) -> bool:
    """Exact line-by-line match, ignoring only CRLF and trailing whitespace."""
    return _norm(expected) == _norm(actual)


def venv_bin(venv: Path) -> Path:
    return venv / ("Scripts" if os.name == "nt" else "bin")


def find_bash() -> str:
    """A POSIX bash: on Windows, Git Bash, never the WSL launcher."""
    path = os.environ.get("PATH", "")
    for d in path.split(os.pathsep):
        exe = shutil.which("bash", path=d) if d else None
        if exe is None:
            continue
        low = exe.lower()
        if os.name == "nt" and ("\\system32\\" in low or "\\windowsapps\\" in low):
            continue
        return exe
    git = shutil.which("git")
    if os.name == "nt" and git:
        cand = Path(git).resolve().parent.parent / "bin" / "bash.exe"
        if cand.is_file():
            return str(cand)
    raise ReadmeError("no bash found: the Quick Start's CLI block needs a POSIX shell (pass --bash)")


def _run(argv: list[str], cwd: Path, env: dict[str, str]) -> tuple[int, str]:
    proc = subprocess.run(  # noqa: S603 — argv built from the venv and the README, no shell=True
        argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900, check=False
    )
    return proc.returncode, proc.stdout.decode("utf-8", errors="replace")


def _echo(out: str) -> None:
    print(out, end="" if out.endswith("\n") or not out else "\n")


def run_quickstart(readme: Path, venv: Path, wheel: Path, root: Path, bash: str) -> tuple[float, int]:
    """Install the wheel, run every step; return (seconds to first success, its README line)."""
    steps = plan(quickstart_blocks(readme.read_text(encoding="utf-8")))
    work, scripts = root / "work", root / "blocks"
    scripts.mkdir(parents=True)
    blueprints = readme.parent / "blueprints"
    if not blueprints.is_dir():
        raise ReadmeError(f"{blueprints} not found: the Quick Start runs from a copy of the repo's blueprints/")
    shutil.copytree(blueprints, work / "blueprints")
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["VIRTUAL_ENV"] = str(venv)
    env["PATH"] = str(venv_bin(venv)) + os.pathsep + env.get("PATH", "")
    env["PYTHONUNBUFFERED"] = "1"  # keep stdout/stderr in the order a terminal shows
    python = shutil.which("python", path=str(venv_bin(venv)))
    if python is None:
        raise ReadmeError(f"no python in {venv_bin(venv)}")

    print(f"--- install the wheel built from this commit: {wheel.name}")
    t0 = time.monotonic()
    code, out = _run([python, "-m", "pip", "install", "--progress-bar", "off", str(wheel)], work, env)
    _echo(out)
    if code != 0:
        raise StepFailedError(f"`pip install {wheel.name}` exited {code}")

    first: tuple[float, int] | None = None
    for s in steps:
        if s.kind == "python":
            script = scripts / f"readme_line_{s.line}.py"
            script.write_text(s.source, encoding="utf-8")
            print(f"--- python block (README line {s.line})")
            code, out = _run([python, str(script)], work, env)
            what = f"the python block at README line {s.line}"
        else:
            print(f"$ {s.source}")
            code, out = _run([bash, "-c", s.source], work, env)
            what = f"README line {s.line}: `{s.source}`"
        _echo(out)
        if code != 0:
            raise StepFailedError(f"{what} exited {code}, the README expects 0")
        if s.expected is not None:
            if not output_matches(s.expected, out):
                diff = "\n".join(
                    difflib.unified_diff(_norm(s.expected), _norm(out), "README shows", "printed", lineterm="")
                )
                raise StepFailedError(f"{what} printed something other than the README shows\n{diff}")
            if first is None:
                first = (time.monotonic() - t0, s.line)
    if first is None:
        raise StepFailedError("no Quick Start step shows output, so there is no first success to time")
    return first


def _summary(line: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with Path(path).open("a", encoding="utf-8") as f:
            f.write(f"{line} ({sys.platform}).\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n", 1)[0])
    ap.add_argument("--venv", type=Path, required=True, help="a clean venv to install into")
    ap.add_argument("--dist", type=Path, required=True, help="dir holding exactly one wheel")
    ap.add_argument("--readme", type=Path, default=Path(__file__).resolve().parents[2] / "README.md")
    ap.add_argument("--bash", help="the bash to run the CLI block with (default: found on PATH)")
    args = ap.parse_args(argv)
    with contextlib.suppress(Exception):  # echo the commands' UTF-8 output on any console
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    wheels = sorted(args.dist.glob("*.whl"))
    if len(wheels) != 1:
        print(f"FAIL: {args.dist} must hold exactly one wheel, found {len(wheels)}")
        return 1
    root = Path(tempfile.mkdtemp(prefix="bricks-quickstart-"))
    print(f"Quick Start from {args.readme} in {root / 'work'} (venv {args.venv})")
    try:
        bash = args.bash or find_bash()
        print(f"--- bash: {bash}")
        secs, line_no = run_quickstart(args.readme.resolve(), args.venv.resolve(), wheels[0].resolve(), root, bash)
    except (ReadmeError, StepFailedError) as e:
        print(f"FAIL: {e}")
        _summary(f"README Quick Start FAILED: {str(e).splitlines()[0]}")
        return 1
    finally:
        shutil.rmtree(root, ignore_errors=True)
    line = f"README Quick Start passed: wheel `pip install` to first success (README line {line_no}) in {secs:.1f} s"
    print(line)
    _summary(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
