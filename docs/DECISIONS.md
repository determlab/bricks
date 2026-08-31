# bricks — Decision Ledger

Locked architectural decisions. **Append; never silently re-litigate.**
Issues cite these by number. Superseding a decision is itself a decision.

Process: [`ops/agents/decision-ledger-standard.md`](https://github.com/determlab) v1.0.
Written 2026-08-30 by reading the code, `README.md`, `.agent-loop.yml` and the git
history. These decisions were all made implicitly before this file existed; nothing
here is new policy. Where the code does not yet match a decision, that gap is recorded
below rather than papered over.

| # | Decision | Source |
|---|---|---|
| D1 | **Determinism is the product** — the same blueprint and the same inputs produce the same outputs on every run, forever, with no model in the loop | `README.md`, this doc |
| D2 | **No LLM reaches the execute path** — the engine imports neither `bricks_ai` nor any LLM SDK; violating it fails the build, it is not a preference | import-linter contract `pyproject.toml:77-80`, `tests/core/test_no_ai_imports.py` |
| D3 | **The engine→AI dependency is strictly one-way** — `bricks_ai` imports `bricks`; the CLI's AI commands import lazily behind gates so the engine ships without them | `pyproject.toml:81-82`, `src/bricks/cli/main.py`, `README.md` |
| D4 | **A blueprint is data, not code** — plain YAML that can be diffed, versioned and reviewed; loading one never imports or executes caller-supplied Python | `src/bricks/core/loader.py`, `src/bricks/core/models.py` |
| D5 | **A brick is a plain typed Python function returning a dict** — registered by the `@brick` decorator, with no base class to inherit and no framework types in the signature | `src/bricks/core/brick.py:105`, `src/bricks/BRICK_STYLE_GUIDE.md` |
| D6 | **Execution is sequential; the DAG is compile-time only** — the engine walks `blueprint.steps` in order, and the DAG exists to linearise the `@flow` Python DSL into that list | `src/bricks/core/engine.py:147`, `CHANGELOG.md` 0.5.0 |
| D7 | **Third-party bricks arrive through the `bricks.packs` entry point** — installing a pack is the supported extension mechanism; the engine does not scan paths or import by name | `pyproject.toml:43-44`, `src/bricks/packs.py` |
| D8 | **A failure names the step that caused it** — errors are attributed to a specific step and brick, never to the pipeline as a whole | `src/bricks/core/exceptions.py`, `tests/core/test_engine_attribution.py` |
| D9 | **The engine is `mypy --strict`** — the type contract is machine-checked in CI, not aspirational | `pyproject.toml:85-86`, `.github/workflows/ci.yml` |
| D10 | **Pre-1.0, the public API may change in a minor release** — the guarantee is a `CHANGELOG.md` entry, not API stability | `CHANGELOG.md`, `.agent-loop.yml` (`flag_on_public_api_change: false`) |
| D11 | **The human gate is at the issue, not the merge** — only the founder applies `agent:go`; after that, a reviewer PASS plus green CI is sufficient to merge | `.agent-loop.yml` (decision 2026-07-19) |
| D12 | **Auto-merge requires a required CI status check** — the loop never merges into an unprotected branch, whatever the config says | `.agent-loop.yml`, agent-loop `loop-contract.md` |

## Gaps against locked decisions

Each of these is a decision that is **true as intent and false in the code today**. Per
the ledger standard §8, each is an issue waiting to be written — pre-cited and
pre-scoped. None is a new decision; they are all debts against decisions above.

| Gap | Against | Evidence |
|---|---|---|
| G1 | D1 | Four stdlib bricks read the clock or a CSPRNG: `date_time.py:99` (`datetime.now`), `date_time.py:184` (`.date()` on now), `encoding_security.py:140` (`uuid4`), `encoding_security.py:171` (`secrets.choice`). A blueprint using any of them is not reproducible. |
| G2 | D1 | `Node.id` defaults to a fresh `uuid4` (`dsl.py:105`), so `flow.to_yaml()` emits different text on every run for an identical flow. The compiler is not reproducible even when the pipeline is. |
| G3 | D1 | No test runs a blueprint twice and compares the outputs. The product's central claim has no regression test. |
| G4 | D4 | Guard conditions are evaluated with a bare `eval()` (`engine.py:346`), with `__builtins__` emptied and step results as locals. Emptying builtins is a well-known incomplete sandbox. A blueprint is therefore data *except* in guard conditions, where it is code. |
| G5 | D4 | `README.md:48` says DSL expressions "are checked against an AST whitelist, so blueprints can't smuggle in arbitrary code". The whitelist (`PythonDSLValidator`, `validator_dsl.py`) is real but is called by nothing in the execute path — it exists for the LLM-generated Python DSL. YAML guard conditions reach `eval` unchecked. The claim conflates two different paths. |
| G6 | D5 | `README.md:32` says a blueprint is "validated against typed brick signatures *before* it runs". `BlueprintValidator` checks brick existence, reference resolution, unique `save_as`, no forward references and step count — **no type checking of any kind**. The claim is not true anywhere in the codebase. |
| G7 | D9 | `bricks.stdlib.*` is exempted with `ignore_errors = true` (`pyproject.toml:110-112`). The 101 stdlib bricks — the entire product surface a user touches — are excluded from the strict type check. |
| G8 | — | The two public entry points disagree on safety. `run_blueprint()` validates (`api.py:86`); the CLI's `bricks run` constructs the engine directly and does not (`cli/main.py:242`). Only `check` and `dry-run` validate. Same operation, different guarantees, depending on how you call it. |
| G9 | — | Roughly 15% of the engine is unreachable scaffolding left over from the bricks/bricks-ai split: `boot/` is imported by nothing, `core/filtering_selector.py` is imported by nothing, and `core/validator_dsl.py` is reachable only through `core/__init__.py`'s re-export. |

## Open decisions

Named, not yet decided. **An issue that needs one of these is not ready for `agent:go`.**

- **O1 — Is determinism enforced, or advertised?** D1 is the product thesis and nothing in the code defends it (G1–G3). Options: mark non-deterministic bricks with a `deterministic=False` flag and refuse them in a strict mode; move them to a separate pack; or accept them and narrow the claim. Settled by deciding what `run_blueprint` guarantees a caller.
- **O2 — What replaces `eval` for guard conditions?** (G4) Options: apply the existing AST whitelist to guards; replace with a restricted expression grammar; or keep `eval` and document blueprints as trusted input. Settled by deciding whether a blueprint from an untrusted source is in the threat model at all.
- **O3 — Does `bricks run` validate?** (G8) Aligning the CLI with the Python API costs a little startup time and turns some runtime failures into pre-flight ones. Settled by deciding whether `run` is "execute exactly what I wrote" or "execute if it is sound".
- **O4 — Does the validator gain type checking, or does the claim get withdrawn?** (G6) These are the only two honest options. The README currently promises something that does not exist.
- **O5 — Is `bricks.stdlib` type-checked?** (G7) Lifting the exemption is real work across 101 bricks; leaving it means "mypy --strict" describes the engine only. Settled by deciding whether D9 covers the product surface or just the core.
- **O6 — Delete the dead scaffolding, or keep it as a seam?** (G9) `selector/`, `boot/`, `catalog.py`, `filtering_selector.py`, `validator_dsl.py` are inert here but may be the intended extension points for `bricks_ai`. Settled by asking whether `bricks_ai` imports them today.
- **O7 — What is the PyPI name?** `bricks` is taken by an unrelated abandoned project. Nothing ships until this is answered, so it blocks the 0.5.0 release recorded in `CHANGELOG.md`.

## Superseded

*None yet. A decision replaced by another moves here with its replacement and the date.*
