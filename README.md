# Bricks

[![CI](https://github.com/hemipaska-maker/bricks/actions/workflows/ci.yml/badge.svg)](https://github.com/hemipaska-maker/bricks/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**A deterministic execution engine for typed Python building blocks. No LLM. No tokens. Same input, same output, every time.**

Bricks validates and executes pipelines ("blueprints") built from small, typed, pre-tested
functions ("bricks"). Blueprints are plain YAML — inspectable, versionable, auditable. The engine
is pure Python with zero AI dependencies: pydantic, typer, ruamel.yaml, rich. That's it.

> Looking for the AI layer — composing blueprints from natural language with an LLM?
> That lives in the companion package [`bricks-ai`](https://github.com/hemipaska-maker/bricks-ai),
> which builds on this engine. The engine never imports it (enforced by import-linter in CI).

---

## Install

```bash
pip install -e .            # from a clone; PyPI release TBD
```

The base install ships:

- The execution engine: blueprint loading, validation (AST whitelist for DSL), DAG execution
- **100 stdlib bricks** (data, string, math, date/time, validation, list ops, encoding)
- The blueprint store (file/memory cache)
- The `bricks` CLI

## Quick Start — Python API

```python
from bricks import run_blueprint

result = run_blueprint("blueprints/crm_pipeline.yaml", inputs={"data": customers})
print(result.outputs)
```

Or with an explicit registry:

```python
from bricks import build_default_registry, run_blueprint

registry = build_default_registry()   # all installed brick packs + DSL builtins
result = run_blueprint(yaml_string, inputs={...}, registry=registry)
```

## Quick Start — CLI

```bash
bricks run blueprints/crm_pipeline.yaml -i data='[...]'   # execute a blueprint
bricks check blueprints/crm_pipeline.yaml                 # validate without executing
bricks dry-run blueprints/crm_pipeline.yaml               # full dry-run
bricks list                                               # list registered bricks
bricks new brick my_brick                                 # scaffold a brick
bricks store seed blueprints/                             # seed the blueprint cache
```

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
from bricks import step, for_each, branch, flow

@flow
def clean_pipeline(data):
    cleaned = step.clean(text=data)
    return step.summarize(text=cleaned)

blueprint = clean_pipeline.to_blueprint()   # → BlueprintDefinition
yaml_str  = clean_pipeline.to_yaml()        # → YAML string
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
