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

**Doc commands (bricks#105).** ``doc_commands()`` is a second, lenient extractor
reused by ``tests/test_readme_commands.py``, not by this script's own ``main()``.
Unlike ``quickstart_blocks()`` above, it needs no marker: every ``bash``/``sh``
fenced block (plain or indented, inside a list item or not) runs unless the
nearest non-blank line above it is ``<!-- doc-test: skip <reason> -->`` (never
run) or ``<!-- doc-test: main-only <reason> -->`` (run only when ``RC_WHEELS``
is set — see ``resolve_doc_commands()``). A command's expected output comes from
whichever the docs show: ``#`` lines directly under it, a plain fenced block
right after its block, or a following ``prints `...`.`` sentence; a following
``Exit N.`` sentence is its expected exit code (default 0). None of that is
retyped here — it is read out of the file each run.

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


# --- Doc commands (bricks#105): lenient bash/sh extraction for README's first screen
# and all of AGENTS.md, reusing everything above instead of a third mechanism. ---

MAX_DOC_TEST_SKIPS = 2  # shal PR 360 started at 4; the CTO asked for 2 — a constant, not a setting.

_FENCE_LENIENT = re.compile(r"^```\s*([\w-]*)\s*$")
_DOC_SKIP = re.compile(r"^<!--\s*doc-test:\s*skip\s+(.+?)\s*-->$")
_DOC_MAIN_ONLY = re.compile(r"^<!--\s*doc-test:\s*main-only\s+(.+?)\s*-->$")
_EXIT_PROSE = re.compile(r"^Exit\s+(\d+)\.")
_PRINTS_PROSE = re.compile(r"^prints?\s+`([^`]+)`")
_CD = re.compile(r"^cd\s+(\S+)$")
_GIT_CLONE = re.compile(r"^git clone\s+(\S+)(.*)$")
_PIP_INSTALL = re.compile(r"^pip install\b")
# The repo's own README/AGENTS.md install line: cloning it for real would test
# `main`, not this commit (the same reason the wheel stands in for it above).
KNOWN_REMOTES = {"https://github.com/determlab/bricks.git", "https://github.com/determlab/bricks"}


class DocSkipError(Exception):
    """A doc command is marked `<!-- doc-test: skip|main-only <reason> -->` and was not run."""


@dataclass
class DocCommand:
    file: str
    line: int  # 1-based line of the command, in *file*
    command: str
    expected: list[str] | None
    expected_exit: int
    skip_reason: str | None
    main_only_reason: str | None


@dataclass
class ResolvedDocCommand:
    file: str
    line: int
    command: str
    expected: list[str] | None
    expected_exit: int
    skipped: str | None  # the reason it will not run, or None to run it


def first_screen(readme: str) -> str:
    """README text up to the first ``## `` heading that follows a ``## Quick Start`` one.

    "The first screen" per bricks#105: ``## Why Bricks?``, ``## Install`` and every
    ``## Quick Start`` section, stopping before whatever heading comes after them. A
    README with no Quick Start heading is returned whole — ``quickstart_blocks()``
    is what raises on that, and this function has no opinion about it.
    """
    lines = readme.replace("\r\n", "\n").split("\n")
    seen_quickstart = False
    for i, ln in enumerate(lines):
        if ln.startswith("## "):
            if _SECTION.match(ln):
                seen_quickstart = True
            elif seen_quickstart:
                return "\n".join(lines[:i])
    return readme


def _attach_prose_output(lines: list[str], after: int, cmd: DocCommand) -> None:
    """Fill *cmd*'s expected output/exit code from whatever immediately follows its block."""
    n = len(lines)
    peek = after
    blanks = 0
    while peek < n and not lines[peek].strip():
        peek += 1
        blanks += 1
    if blanks <= 1 and peek < n:
        fm = _FENCE_LENIENT.match(lines[peek].strip())
        if fm and fm.group(1) == "":
            j = peek + 1
            out_body: list[str] = []
            while j < n and lines[j].strip() != "```":
                out_body.append(lines[j])
                j += 1
            if j < n:  # the output fence closed properly; an unclosed one is just prose
                cmd.expected = list(out_body)
                peek = j + 1
                while peek < n and not lines[peek].strip():
                    peek += 1
    if peek < n:
        prose = lines[peek].strip()
        em = _EXIT_PROSE.match(prose)
        if em:
            cmd.expected_exit = int(em.group(1))
        if cmd.expected is None:
            pm = _PRINTS_PROSE.match(prose)
            if pm:
                cmd.expected = [pm.group(1)]


def doc_commands(text: str, filename: str) -> list[DocCommand]:
    """Every command in every ``bash``/``sh`` fenced block of *text*, in order.

    Lenient, unlike ``quickstart_blocks()``: no marker is required, a fence may be
    indented (inside a list item), and a block with no `#`-commented output picks up
    its expected output or exit code from the prose right after it (see module
    docstring). A block whose nearest non-blank line above it is a `doc-test` marker
    is still returned, carrying the skip/main-only reason instead of being dropped —
    resolving it (run or not) is `resolve_doc_commands()`'s job, since that depends on
    `RC_WHEELS`.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    n = len(lines)
    out: list[DocCommand] = []
    last_text = ""
    i = 0
    while i < n:
        stripped = lines[i].strip()
        m = _FENCE_LENIENT.match(stripped)
        if not m:
            if stripped:
                last_text = stripped
            i += 1
            continue
        lang = m.group(1).lower()
        open_line = i + 1
        i += 1
        body_start = i
        while i < n and lines[i].strip() != "```":
            i += 1
        if i >= n:
            raise ReadmeError(f"{filename} line {open_line}: code fence never closed")
        body = lines[body_start:i]
        i += 1  # consume the closing fence
        if lang not in ("bash", "sh"):
            last_text = "```"
            continue
        skip = _DOC_SKIP.match(last_text)
        main_only = _DOC_MAIN_ONLY.match(last_text)
        last_text = "```"
        block: list[DocCommand] = []
        current: DocCommand | None = None
        for k, row in enumerate(body):
            line_no = body_start + 1 + k
            s = row.strip()
            if not s:
                current = None
            elif s.startswith("#"):
                if current is not None:
                    current.expected = [*(current.expected or []), _comment(s)]
            else:
                current = DocCommand(
                    file=filename,
                    line=line_no,
                    command=s,
                    expected=None,
                    expected_exit=0,
                    skip_reason=skip.group(1).strip() if skip else None,
                    main_only_reason=main_only.group(1).strip() if main_only else None,
                )
                block.append(current)
        if len(block) == 1 and block[0].expected is None:
            _attach_prose_output(lines, i, block[0])
        out.extend(block)
    return out


def localize_git_clone(command: str, repo_root: Path) -> str:
    """Clone this checkout instead of the network (bricks#105): the README's own
    `git clone` line is for a stranger, not for testing the commit under test — the
    same reason `run_quickstart()` installs a wheel instead of running it."""
    m = _GIT_CLONE.match(command)
    if not m or m.group(1) not in KNOWN_REMOTES:
        return command
    return f"git clone {repo_root}{m.group(2)}"


def resolve_doc_commands(commands: list[DocCommand], rc_wheels: str | None) -> list[ResolvedDocCommand]:
    """Decide what runs. `skip` never runs. `main-only` runs only when *rc_wheels* is
    set (it needs a release PyPI does not have yet); otherwise it is skipped, visibly,
    with its own reason. A `pip install` line runs against *rc_wheels* when set
    (``--no-index --find-links``), against PyPI otherwise — never retyped here."""
    out = []
    for c in commands:
        if c.skip_reason:
            out.append(ResolvedDocCommand(c.file, c.line, c.command, c.expected, c.expected_exit, c.skip_reason))
            continue
        if c.main_only_reason and not rc_wheels:
            out.append(ResolvedDocCommand(c.file, c.line, c.command, c.expected, c.expected_exit, c.main_only_reason))
            continue
        command = c.command
        if rc_wheels and _PIP_INSTALL.match(command):
            command = command.replace("pip install", f'pip install --no-index --find-links "{rc_wheels}"', 1)
        out.append(ResolvedDocCommand(c.file, c.line, command, c.expected, c.expected_exit, None))
    return out


@dataclass
class DocRunner:
    """Runs resolved doc commands in order, tracking `cd` the way a reader's shell would
    (each command is its own subprocess, so a real `cd` would not otherwise persist)."""

    bash: str
    env: dict[str, str]
    cwd: Path
    repo_root: Path | None = None

    def run(self, cmd: ResolvedDocCommand) -> None:
        if cmd.skipped:
            raise DocSkipError(cmd.skipped)
        cd = _CD.match(cmd.command)
        if cd:
            new_cwd = (self.cwd / cd.group(1)).resolve()
            if not new_cwd.is_dir():
                raise StepFailedError(f"{cmd.file}:{cmd.line}: `{cmd.command}`: no such directory {new_cwd}")
            self.cwd = new_cwd
            return
        command = cmd.command
        if self.repo_root is not None:
            command = localize_git_clone(command, self.repo_root)
        code, actual = _run([self.bash, "-c", command], self.cwd, self.env)
        if code != cmd.expected_exit:
            raise StepFailedError(
                f"{cmd.file}:{cmd.line}: `{cmd.command}` exited {code}, the docs expect {cmd.expected_exit}\n{actual}"
            )
        if cmd.expected is not None and not output_matches(cmd.expected, actual):
            diff = "\n".join(
                difflib.unified_diff(_norm(cmd.expected), _norm(actual), "docs show", "printed", lineterm="")
            )
            what = f"{cmd.file}:{cmd.line}: `{cmd.command}`"
            raise StepFailedError(f"{what} printed something other than the docs show\n{diff}")


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
