"""Tests for the README Quick Start extractor in dev/quickstart/run_readme.py (#41)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_readme", ROOT / "dev" / "quickstart" / "run_readme.py")
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["run_readme"] = mod  # dataclasses look the module up while building the classes
    spec.loader.exec_module(mod)
    return mod


rr = _load()

FENCE = "```"


def _readme(*parts: str) -> str:
    return "# Title\n\n" + "\n".join(parts)


PY_RUN = f"""## Quick Start — Python

<!-- quickstart: run -->
{FENCE}python
print("hi")
# hi
{FENCE}
"""

SH_RUN = f"""## Quick Start — CLI

<!-- quickstart: run -->
{FENCE}bash
echo 'a b'
# a b

echo one   # a note, not output
echo two
{FENCE}
"""


def test_real_readme_has_a_runnable_python_and_cli_quick_start() -> None:
    # Structure only. The README is the source: pinning its words here would be a
    # copy of it, and a wording change by its owner would break the unit suite.
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    blocks = rr.quickstart_blocks(readme)  # raises if any Quick Start block lacks a marker
    assert {b.marker for b in blocks} <= {"run", "skip"}
    run_langs = {b.lang for b in blocks if b.marker == "run"}
    assert {"python", "bash"} <= run_langs
    steps = rr.plan(blocks)
    for lang in ("python", "bash"):
        assert any(s.kind == lang and s.expected and any(ln.strip() for ln in s.expected) for s in steps), lang


def test_bash_output_belongs_to_the_command_above_it() -> None:
    steps = rr.plan(rr.quickstart_blocks(_readme(PY_RUN, SH_RUN)))
    sh = [(s.source, s.expected) for s in steps if s.kind == "bash"]
    assert sh == [
        ("echo 'a b'", ["a b"]),
        ("echo one   # a note, not output", None),
        ("echo two", None),
    ]


def test_python_block_code_and_trailing_comments() -> None:
    (step,) = [s for s in rr.plan(rr.quickstart_blocks(_readme(PY_RUN, SH_RUN))) if s.kind == "python"]
    assert step.source == 'print("hi")\n'
    assert step.expected == ["hi"]


def test_skip_block_is_not_run_and_blocks_outside_quick_start_are_ignored() -> None:
    skip = f"<!-- quickstart: skip -->\n{FENCE}python\nrun(x, inputs={{...}})\n{FENCE}\n"
    outside = f"## Development\n\n{FENCE}bash\npytest\n{FENCE}\n"
    steps = rr.plan(rr.quickstart_blocks(_readme(PY_RUN + skip, SH_RUN, outside)))
    assert [s.source for s in steps if s.kind == "python"] == ['print("hi")\n']
    assert "pytest" not in [s.source for s in steps]


def test_unmarked_block_in_quick_start_fails() -> None:
    unmarked = f"{FENCE}python\nprint(1)\n{FENCE}\n"
    with pytest.raises(rr.ReadmeError, match="no `<!-- quickstart: run -->`"):
        rr.quickstart_blocks(_readme(PY_RUN + "\n" + unmarked, SH_RUN))


def test_marker_does_not_carry_to_the_next_block() -> None:
    second = f"\n{FENCE}python\nprint(2)\n{FENCE}\n"
    with pytest.raises(rr.ReadmeError, match="marker"):
        rr.quickstart_blocks(_readme(PY_RUN + second, SH_RUN))


@pytest.mark.parametrize(("parts", "lang"), [((SH_RUN,), "python"), ((PY_RUN,), "bash")])
def test_a_missing_python_or_cli_block_fails(parts: tuple[str, ...], lang: str) -> None:
    with pytest.raises(rr.ReadmeError, match=f"no ```{lang} block"):
        rr.plan(rr.quickstart_blocks(_readme(*parts)))


def test_no_quick_start_section_fails() -> None:
    with pytest.raises(rr.ReadmeError, match="no '## Quick Start'"):
        rr.quickstart_blocks("# Title\n\n## Install\n")


def test_continued_command_line_fails() -> None:
    cont = f"## Quick Start\n\n<!-- quickstart: run -->\n{FENCE}bash\nbricks run \\\n  x.yaml\n{FENCE}\n"
    with pytest.raises(rr.ReadmeError, match="continued command"):
        rr.plan(rr.quickstart_blocks(_readme(PY_RUN, cont)))


def test_blank_line_between_command_and_its_output_fails() -> None:
    gap = f"## Quick Start\n\n<!-- quickstart: run -->\n{FENCE}bash\necho hi\n\n# hi\n{FENCE}\n"
    with pytest.raises(rr.ReadmeError, match="directly under its command"):
        rr.plan(rr.quickstart_blocks(_readme(PY_RUN, gap)))


@pytest.mark.parametrize("fence", ["~~~bash", "  ```bash"])
def test_tilde_or_indented_fence_in_quick_start_fails(fence: str) -> None:
    odd = f"## Quick Start\n\n<!-- quickstart: run -->\n{fence}\necho hi\n{fence.strip()[:3]}\n"
    with pytest.raises(rr.ReadmeError, match="no ~~~, no indent"):
        rr.quickstart_blocks(_readme(PY_RUN, SH_RUN, odd))


def test_output_match_ignores_crlf_and_trailing_space_only() -> None:
    shown = ["Job 'x' done.", "  count: 2"]
    assert rr.output_matches(shown, "Job 'x' done.  \r\n  count: 2\r\n\r\n")
    assert not rr.output_matches(shown, "Job 'x' ended.\n  count: 2\n")
    assert not rr.output_matches(shown, "Job 'x' done.\ncount: 2\n")
    assert not rr.output_matches(shown, "Job 'x' done.\n")
