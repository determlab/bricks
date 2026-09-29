"""AGENTS.md must name every CLI command, and every --json command in its --json sentence."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import typer.main

from bricks.cli.main import app

AGENTS_MD = Path(__file__).resolve().parent.parent / "AGENTS.md"


def _walk(group: Any, prefix: str = "") -> list[tuple[str, Any]]:
    """Return (space-joined path, command) for every leaf command under *group*."""
    found: list[tuple[str, Any]] = []
    for name, sub in getattr(group, "commands", {}).items():
        path = f"{prefix} {name}".strip()
        if hasattr(sub, "commands"):
            found.extend(_walk(sub, path))
        else:
            found.append((path, sub))
    return found


def _commands() -> list[tuple[str, Any]]:
    commands = _walk(typer.main.get_command(app))
    assert commands, "no CLI commands found"
    return commands


def test_every_cli_command_is_named_in_agents_md() -> None:
    text = AGENTS_MD.read_text(encoding="utf-8")
    missing = [path for path, _ in _commands() if f"`{path}`" not in text]
    assert not missing, f"AGENTS.md does not name these CLI commands: {missing}"


def test_every_json_command_is_named_in_the_json_sentence() -> None:
    text = AGENTS_MD.read_text(encoding="utf-8")
    match = re.search(r"\. ([^.]*?) take `--json`", text)
    assert match, "AGENTS.md has no sentence of the form '... take `--json`'"
    sentence = match.group(1)
    json_commands = [path for path, cmd in _commands() if any("--json" in p.opts for p in cmd.params)]
    assert json_commands, "no command with a --json option found"
    missing = [path for path in json_commands if f"`{path}`" not in sentence]
    assert not missing, f"the --json sentence in AGENTS.md does not name: {missing}"
