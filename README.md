# Bricks

[![CI](https://github.com/determlab/bricks/actions/workflows/ci.yml/badge.svg)](https://github.com/determlab/bricks/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Status:** alpha (`0.5.x`) — APIs may change between minor versions. PyPI release planned.

**The deterministic execution layer for AI systems. An agent composes a pipeline once; Bricks runs it forever — no LLM in the loop, no tokens per run, same output every time.**

Bricks validates and executes pipelines ("blueprints") built from small, typed, pre-tested
functions ("bricks"). Blueprints are plain YAML — inspectable, versionable, auditable. The engine
is pure Python with zero AI dependencies: pydantic, typer, ruamel.yaml, rich. That's it.
832 tests, `mypy --strict`, and an import-linter contract in CI guarantee it stays that way.

> Want an LLM to *compose* blueprints from natural language? That's
> [`bricks-ai`](https://github.com/hemipaska-maker/bricks-ai) — see
> [Relationship to bricks-ai](#relationship-to-bricks-ai).

---

## Why Bricks?

LLM agents are good at deciding *what* to do — and unreliable at *doing* it the same way
twice. Every run costs tokens, every retry can produce different output, and nobody can
audit a pipeline that might improvise.

Bricks splits the work: an LLM (or a human) composes a pipeline **once**, then the engine
runs it forever with no model in the loop. Zero tokens per run. Same output, every run.

**"I could just write a Python script."** You could — but a blueprint is what a script
can't be: data instead of code. It's validated against typed brick signatures *before* it
runs, diffed and versioned like config, and executed step-by-step with errors attributed
to the exact brick that failed. A script does what it does; a blueprint can show what it
will do before it does it.

## Install

```bash
git clone https://github.com/determlab/bricks.git
cd bricks
pip install -e .        # PyPI release planned
```

The base install ships:

- The execution engine: blueprint loading, DAG execution, and validation — DSL expressions
  are checked against an AST whitelist, so blueprints can't smuggle in arbitrary code
- **101 stdlib bricks** (data, string, math, date/time, validation, list ops, encoding)
- The blueprint store — caches validated blueprints (file or in-memory) so repeated tasks
  reuse a known-good pipeline instead of rebuilding it
- The `bricks` CLI

## Quick Start — Python API

```python
from bricks import run_blueprint

crm_json = """[
  {"name": "Acme",    "status": "active",  "monthly_revenue": 4200},
  {"name": "Globex",  "status": "churned", "monthly_revenue": 1800},
  {"name": "Initech", "status": "active",  "monthly_revenue": 3100}
]"""

result = run_blueprint("blueprints/crm_pipeline.yaml", inputs={"crm_json": crm_json})
print(result.outputs)
# {'active_count': 2, 'total_active_revenue': 7300, 'avg_active_revenue': 3650.0}
```

Run it a thousand times — same three numbers, every time. That's the point.

Or with an explicit registry:

```python
from bricks import build_default_registry, run_blueprint

registry = build_default_registry()   # all installed brick packs + DSL builtins
result = run_blueprint(yaml_string, inputs={...}, registry=registry)
```

## Quick Start — CLI

```bash
bricks run blueprints/crm_pipeline.yaml -i crm_json='[...]'   # execute a blueprint
bricks check blueprints/crm_pipeline.yaml                     # validate without executing
bricks list                                                   # list registered bricks
bricks new brick my_brick                                     # scaffold a brick
bricks store seed blueprints/                                 # seed the blueprint cache
```

> `bricks dry-run` is currently an alias for `check`.

Example blueprints live in [blueprints/](blueprints/).

## Writing a Brick

```python
from bricks.core.brick import brick

@brick(tags=["math"], description="Add two numbers")
def add(a: float, b: float) -> dict[str, float]:
    return {"result": a + b}
```

Bricks are plain typed functions. The full catalog of stdlib bricks is in
[docs/BRICK_CATALOG.md](docs/BRICK_CATALOG.md); conventions are in
[src/bricks/BRICK_STYLE_GUIDE.md](src/bricks/BRICK_STYLE_GUIDE.md).

## Python DSL

Write pipelines as Python instead of YAML — the `@flow` decorator traces the function once and
builds a DAG:

```python
from bricks import step, flow

@flow
def active_revenue(crm_json):
    parsed   = step.extract_json_from_str(text=crm_json)
    active   = step.filter_dict_list(items=parsed.output, key="status", value="active")
    revenues = step.map_values(items=active.output, key="monthly_revenue")
    return step.reduce_sum(values=revenues.output)

blueprint = active_revenue.to_blueprint()   # → BlueprintDefinition
yaml_str  = active_revenue.to_yaml()        # → the same YAML you'd write by hand
```

## Community Packs

Publish a `bricks-{name}` package with a `bricks.packs` entry point and it auto-registers:

```toml
# your-package/pyproject.toml
[project.entry-points."bricks.packs"]
mypack = "bricks_mypack"
```

```python
# bricks_mypack/__init__.py
from bricks.core.brick import brick
from bricks.core.registry import BrickRegistry

@brick(description="Fetch from my API")
def fetch_my_api(endpoint: str) -> dict:
    ...

def register(registry: BrickRegistry) -> None:
    registry.register("fetch_my_api", fetch_my_api, fetch_my_api.__brick_meta__)
```

## Relationship to bricks-ai

| Package | Role | LLM |
|---|---|---|
| **bricks** (this repo) | Deterministic execution: validate + run blueprints | None |
| [**bricks-ai**](https://github.com/hemipaska-maker/bricks-ai) | Compose blueprints from natural language, healing, providers, playground, MCP | Yes |

The dependency is strictly one-way: `bricks_ai` imports `bricks`. The CLI's AI commands
(`compose`, `demo`, `serve`, `playground`) are gated — they print an install hint unless the AI
package is present. CI enforces the boundary with import-linter and a guard test
(`tests/core/test_no_ai_imports.py`).

## Development

```bash
pip install -e ".[dev]"
pytest                       # full engine test suite
ruff check . && ruff format --check .
mypy src/bricks              # strict
lint-imports                 # engine must not import bricks_ai
```

## License

MIT — see [LICENSE](LICENSE).
