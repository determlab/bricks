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


def test_real_readme_plans_python_and_cli_with_shown_output() -> None:
    steps = rr.plan(rr.quickstart_blocks((ROOT / "README.md").read_text(encoding="utf-8")))
    py = [s for s in steps if s.kind == "python"]
    sh = [s for s in steps if s.kind == "bash"]
    assert len(py) == 1  # the explicit-registry block is marked skip
    assert "run_blueprint(" in py[0].source
    assert py[0].expected == ["{'active_count': 2, 'total_active_revenue': 7300, 'avg_active_revenue': 3650.0}"]
    assert sh[0].source.startswith("bricks run blueprints/crm_pipeline.yaml -i crm_json='[")
    assert sh[0].expected == [
        "Blueprint 'crm_pipeline' completed.",
        "Outputs:",
        "  active_count: 2",
        "  total_active_revenue: 7300",
        "  avg_active_revenue: 3650.0",
    ]
    rest = [s.source.split("#")[0].strip() for s in sh[1:]]
    assert rest == [
        "bricks check blueprints/crm_pipeline.yaml",
        "bricks list",
        "bricks new brick my_brick",
        "bricks store seed blueprints/",
    ]
    assert all(s.expected is None for s in sh[1:])


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


def test_output_match_ignores_crlf_and_trailing_space_only() -> None:
    shown = ["Blueprint 'crm_pipeline' completed.", "  active_count: 2"]
    assert rr.output_matches(shown, "Blueprint 'crm_pipeline' completed.  \r\n  active_count: 2\r\n\r\n")
    assert not rr.output_matches(shown, "Blueprint 'crm_pipeline' finished.\n  active_count: 2\n")
    assert not rr.output_matches(shown, "Blueprint 'crm_pipeline' completed.\nactive_count: 2\n")
    assert not rr.output_matches(shown, "Blueprint 'crm_pipeline' completed.\n")
