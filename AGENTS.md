---
type: agent-guide
owner: repo-agent
scope: repo/bricks
reviewed: 2026-09-27
---

# AGENTS.md — using bricks

## What bricks does

bricks runs a pipeline written as a YAML file (a "blueprint") that names small typed
Python functions ("bricks") and the order to call them in. There is no model in the
run: the same blueprint and the same inputs give the same outputs every time.

## Install

bricks is not on PyPI yet. Install from a clone (Python 3.10 to 3.12):

```bash
git clone https://github.com/determlab/bricks.git
cd bricks
pip install -e .
```

## First success

No account, no API key, no config file. Run this from the `bricks` folder; it runs
the example blueprint `blueprints/crm_pipeline.yaml` through the Python API:

```bash
python -c "import json, bricks; rows = [dict(name='Acme', status='active', monthly_revenue=4200), dict(name='Globex', status='churned', monthly_revenue=1800), dict(name='Initech', status='active', monthly_revenue=3100)]; print(bricks.run_blueprint('blueprints/crm_pipeline.yaml', inputs={'crm_json': json.dumps(rows)}).outputs)"
```

```
{'active_count': 2, 'total_active_revenue': 7300, 'avg_active_revenue': 3650.0}
```

Exit 0. The numbers never change between runs.

**Use Python, not the CLI, for this today.** `bricks run`, `bricks check` and
`bricks list` load only the bricks named in a `bricks.config.yaml`; they do not load
the built-in stdlib. With no config, `bricks list` prints
`No bricks registered. Check your bricks.config.yaml registry paths.` and
`bricks check blueprints/crm_pipeline.yaml` exits 1 with
`brick 'extract_json_from_str' not found in registry`. A config from `bricks init`
does not fix it (its `registry.paths` is empty).

## How an agent calls it

Python is the working entry point:

- `bricks.run_blueprint(path_or_yaml, inputs={...})` — validate, then run.
  Returns a result whose `.outputs` is a dict. A bad blueprint raises
  `BlueprintValidationError`; a failing step raises `BrickExecutionError`, which
  names the step and the brick:
  `Brick 'divide' failed at step 'avg_revenue': Division by zero: b must not be 0`
  (the example above with `inputs={'crm_json': '[]'}`).
- `bricks.build_default_registry()` — every installed brick (stdlib plus any pack).
- The catalog as data, one dict per brick (name, description, parameters,
  output_keys, destructive, idempotent):

  ```bash
  python -c "import bricks; from bricks.core.schema import registry_schema; s = registry_schema(bricks.build_default_registry()); print(len(s), s[0]['name'])"
  ```

  prints `103 __branch__` (101 stdlib bricks plus 2 DSL builtins).

CLI (`bricks --help` lists all): `run`, `check`, `dry-run`, `list`, `init`, `new`,
`store seed`, `store list`. **No command takes `--json`**; all print text. `compose`,
`demo`, `serve` and `playground` need the separate `bricks-ai` package and an LLM.
`bricks serve` (the MCP server) is one of them: without it, it exits 1 with
`Error: MCP features require the 'mcp' package.` There is no MCP server in this
package.

## Side effects

- `run_blueprint` runs bricks in your process. The stdlib bricks are pure
  functions: no file, network or process calls.
- Each brick declares `destructive` and `idempotent` (from `registry_schema`, or
  `[DESTRUCTIVE]` in `bricks list`). No stdlib brick is destructive. A third-party
  pack sets these flags itself, and the engine does not stop or ask before a
  destructive brick. Check the flag before you run a blueprint that uses one.
- CLI commands that write files: `bricks init` (`bricks.config.yaml`, `blueprints/`,
  `bricks_lib/`), `bricks new brick <name>` (`bricks_lib/<name>.py`) and
  `bricks store seed <dir>` (JSON files in `./blueprint_store`).
- Loading a blueprint never runs code from it, and no string in it is evaluated.

## Where the contract lives

- [docs/DECISIONS.md](docs/DECISIONS.md) — the decision ledger. D1 (determinism),
  D4 and D13 (a blueprint is data, never code) and D8 (errors name the step) bind
  every run. Its gaps (G#) list where the code does not yet keep a decision.
- [src/bricks/core/models.py](src/bricks/core/models.py) — the blueprint format
  (pydantic models the loader validates against).
- [docs/BRICK_CATALOG.md](docs/BRICK_CATALOG.md) — every stdlib brick (generated).
- [src/bricks/BRICK_STYLE_GUIDE.md](src/bricks/BRICK_STYLE_GUIDE.md) — how to write a brick.
- [CHANGELOG.md](CHANGELOG.md) — pre-1.0, the public API may change in a minor release.
- Contributing to this repo, not using it: [docs/agents/context.md](docs/agents/context.md).
