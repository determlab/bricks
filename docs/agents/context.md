---
type: agent-context
owner: repo-agent
scope: repo/bricks
reviewed: 2026-09-03
---

# Bricks — context for the coder and the reviewer

Read this and [`docs/DECISIONS.md`](../DECISIONS.md) before touching anything.
The ledger is the authority; this file is the short version, plus what the code
actually looks like today.

This file is repo-specific by design. The part of the role that is the same in
every product repo — what the repo agent owns, why verifiability rather than
seniority decides that, and the one file it may never change on its own say-so —
is the role charter at `ops/agents/repo-agent.md` in `determlab/ops`. It is not
in this repo and not vendored here; read it there.

## What this is

A deterministic execution engine. A pipeline (a "blueprint") is plain YAML that
names small typed Python functions ("bricks") and the order to run them in. The
engine loads it, validates it, runs it — with no model anywhere in the execute
path. Same blueprint plus same inputs gives the same outputs, forever. That is
the whole product claim (D1).

Composing a blueprint from natural language is a *different* package,
`bricks_ai`. It is not in this repo, and nothing here may import it (D2).

## Architecture

```
src/bricks/api.py             run_blueprint() — load, validate, execute. The public entry point.
src/bricks/core/loader.py     YAML -> BlueprintDefinition (pydantic models in core/models.py)
src/bricks/core/validation.py BlueprintValidator: brick exists, refs resolve, save_as unique,
                              no forward references, step count. No type checking (see G6).
src/bricks/core/engine.py     Walks blueprint.steps in order. Sub-blueprints recurse under a depth cap.
src/bricks/core/brick.py      The @brick decorator. Attaches __brick_meta__; the function stays a function.
src/bricks/core/dsl.py        The @flow Python DSL — traces the function once; dag_builder.py
  + dag*.py                   linearises the DAG into the same step list YAML would produce.
src/bricks/packs.py           Entry-point discovery for the `bricks.packs` group (D7).
src/bricks/stdlib/            101 public bricks across 7 modules; +2 DSL builtins in core/builtins.py.
src/bricks/cli/main.py        The typer CLI. AI commands import lazily behind gates (D3).
src/bricks/store/             The blueprint cache (file or in-memory).
tests/                        840 tests, pytest only.
```

Inert in the engine today, and known to be: `boot/`, `selector/`,
`core/filtering_selector.py`, `core/validator_dsl.py` (G9). Do not build on
them — and do not delete them in passing either, because O6 is still open.

## Rules that are not negotiable

Each cites its ledger row. Breaking one fails review on the Standards axis.

- **The engine never imports `bricks_ai`** (D2, D3). Two things enforce it and
  both fail the build: the import-linter contract at `pyproject.toml:77-84`
  (`type = "forbidden"`, `source_modules = ["bricks"]`, `forbidden_modules =
  ["bricks_ai"]`, with one recorded exemption at `:82-84` for the CLI's gated
  import), and two subprocess tests —
  `tests/core/test_no_ai_imports.py:30` (`test_import_bricks_loads_no_ai_modules`)
  and `:46` (`test_import_engine_cli_loads_no_ai_modules`). The dependency is
  one-way, always.
- **A blueprint is data, not code** (D4). *Loading* one never imports or
  executes caller-supplied Python: `src/bricks/core/loader.py:45` builds
  ruamel's round-trip `YAML()`, not `typ="unsafe"`, so no YAML tag can
  construct an arbitrary Python object. Loading is the whole of that
  guarantee — at run time a guard condition still reaches a bare `eval()`
  (G4, see the next section).
- **A brick is a plain typed function returning a dict** (D5). No base class to
  inherit, no framework types in the signature. Descriptions follow
  [`src/bricks/BRICK_STYLE_GUIDE.md`](../../src/bricks/BRICK_STYLE_GUIDE.md).
- **Execution is sequential; the DAG is compile-time only** (D6).
- **A failure names the step and the brick that caused it** (D8) —
  `BrickExecutionError` at `src/bricks/core/exceptions.py:50`, whose message is
  built from `brick_name` and `step_name` at `:57`. Never a pipeline-level
  "something failed".
- **Third-party bricks arrive through the `bricks.packs` entry point** (D7).
  `run_blueprint()` builds its registry that way and no other:
  `src/bricks/api.py:46` calls `discover_and_load()`, which iterates the
  `bricks.packs` entry-point group at `src/bricks/packs.py:27`. That path scans
  no directories.
  **The CLI is a second path, and it does scan.** `_setup_registry()` at
  `src/bricks/cli/main.py:50-59` calls `discovery.discover_package(p)` or
  `discovery.discover_path(p)` for each entry in `config.registry.paths`, and
  `discover_path` executes the file it finds —
  `src/bricks/core/discovery.py:68-72`, `spec_from_file_location(...)` then
  `spec.loader.exec_module(module)`. It is gated on
  `config.registry.auto_discover`, which is `False` by default
  (`src/bricks/core/config.py:19`) and is turned on by a `bricks.config.yaml`.
  So a default install scans nothing; a configured one imports and runs Python
  from the paths it is given. Whether that second path belongs inside D7 or is
  a gap is **an open question, tracked in determlab/bricks#27** — describe it,
  do not settle it.
- **`mypy --strict` on `src/bricks`** (D9). `bricks.stdlib.*` is exempt today
  (G7) — that is a recorded debt, not a licence to add more exempt code.
- **Pre-1.0 the public API may change in a minor release** (D10) — the price is
  a `CHANGELOG.md` entry, not a version bump.

## The one non-obvious constraint

The ledger records nine gaps (G1–G9) where a locked decision is true as intent
and false in the code. They are known and accepted. **Do not fix one as a side
effect of another issue.** Most are blocked on an open decision (O1–O7), so
"fixing" one silently settles a decision that is not the coder's to settle.

The two you are most likely to trip over:

- YAML guard conditions reach a bare `eval()` (`core/engine.py:346`, builtins
  emptied). So a blueprint is data everywhere *except* there (G4, open as O2).
- `run_blueprint()` validates before it runs; the CLI's `bricks run` builds the
  engine directly and does not (G8, open as O3). Same operation, two different
  guarantees. Do not align them under an unrelated issue.

`README.md` also makes two claims the code does not keep — pre-flight type
checking (G6) and an AST whitelist covering blueprints (G5). Both are recorded.
`README.md` is the CMO's document: do not rewrite it to match the code. File it.

## Build, test, run

```
pip install -e ".[dev]"
python -m pytest
ruff check . && ruff format --check . && mypy src/bricks && lint-imports
python -m build
```

These are the `commands:` block in `.agent-loop.yml`, and they match
`.github/workflows/ci.yml`. CI runs lint once and the test suite on Python
3.10, 3.11 and 3.12. `ruff format` is configured to skip `*.md`.

`docs/BRICK_CATALOG.md` is generated and says so. Never hand-edit it.

## Definition of done

- The issue's acceptance criteria, met literally.
- `python -m pytest` green, and the whole lint line above green — `mypy` and
  `lint-imports` included, not just `ruff`.
- New behaviour comes with a test; a bug fix comes with the test that would
  have caught it.
- No new runtime dependency. The engine's runtime dependencies are pydantic,
  typer, ruamel.yaml, rich, pluggy (the hook system in core/hooks.py), and
  tzdata (Windows only, timezone data for the date_time bricks); editing
  `pyproject.toml` is a hard stop.
- A change to the public surface gets a `CHANGELOG.md` entry under
  `[Unreleased]` (D10).
- If the work would settle, contradict, or supersede a `D#`, or would close a
  `G#` that an `O#` still governs — stop and say so. That is the founder's call.
