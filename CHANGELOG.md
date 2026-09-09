---
type: changelog
owner: repo-agent
scope: repo/bricks
reviewed: 2026-09-01
---

# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Pre-1.0: the public API may change in a minor release. `.agent-loop.yml` sets
`flag_on_public_api_change: false` on that basis, and the reviewer verifies an
entry here instead — so an in-rubric change that alters the public surface must
be recorded below.

That policy was unenforced until 2026-09-01. agent-loop 0.1.0 wrote the key into
every repo and read it nowhere, so the switch was set to `false` and no code
consulted it either way; the only thing between a public-API change and `main`
was the reviewer's own judgement (bricks#20). Plugin 0.2.0 implements it: the
reviewer skips the public-API hard-stop category when the key is `false`, and
says so in its verdict so a silent PASS is not read as "no API change". The
policy above holds from 0.2.0 onward.

## [Unreleased]

### Added
- **A selector measurement, with a recorded baseline.** `TieredCatalog` now has
  a test that runs one 30-task set against it twice — once with
  `CatalogConfig.common_set` holding all 101 stdlib bricks, once with the 14
  `block-set.md` keeps visible — and records what each configuration listed,
  found and missed in `tests/baselines/selector_measurement.md`. Fourteen tasks
  have an answer inside the small set and sixteen deliberately do not.

  Tier 1 hits 30/30 at 101 bricks and 14/30 at 14; every one of those 16 misses
  is recovered by a single tier-2 search. The cost of the full listing is
  precision 0.0099 against 0.0714, and a mean of 3.00 same-keyword rivals beside
  the right answer against 0.37. The measurement has no model in it, so it
  reports what a caller is *shown*, not what a model would *pick*.

  Test-only: no engine behaviour changed. Regenerate the baseline with
  `BRICKS_UPDATE_BASELINE=1 python -m pytest tests/core/test_selector_measurement.py`.
  (#31, `tool-set.md` R6)

### Changed
- **A `type: guard` step names a brick instead of carrying a Python
  expression.** The engine no longer calls `eval` on anything from a
  blueprint: it looks the brick up in the registry, calls it with the step's
  resolved `params`, and takes the truthiness of its result — the same rule
  `__branch__` already applies to `condition_brick`. `src/bricks/core/` now
  contains no `eval(` and no `exec(`, and CI greps for it. (#17, RFC-002, D13)

  A guard whose predicate *raises* now fails with `BrickExecutionError` naming
  that brick and step (D8), not `GuardFailedError`. Teardown now runs for guard
  steps — on the guard's own brick first, then in reverse order over the steps
  already completed — for both a raised predicate and a failed guard.

  `GuardFailedError.__init__` takes `brick_name=` in place of `condition=`, and
  the instance attribute `.condition` is gone, replaced by `.brick_name` (D10).
  The `condition` field is removed from `StepDefinition`; a guard step must set
  `brick`, and may not set `blueprint`.

  ***Upgrading:*** replace the guard's `condition:` expression with a `brick:`
  naming a predicate brick and the values it needs under `params:`. A guard
  that read `condition: "todays['result']"` becomes:

  ```yaml
  - name: enough_events
    type: guard
    brick: is_not_empty
    params:
      value: "${todays.result}"
    message: "no events today"
  ```

  A comparison such as `condition: "count['result'] > 3"` becomes
  `brick: compare_values` with `params: {a: "${count.result}", b: 3,
  operator: gt}`. Compound conditions become two guards in sequence. No
  shipped blueprint used the old form, so there is nothing to migrate; an
  old-form guard now fails loudly with `Guard step must specify 'brick'`.

### Fixed
- `pluggy` is now a declared runtime dependency. `import bricks.core.hooks`
  raised `ModuleNotFoundError` on a plain (non-`[dev]`) install, because
  pluggy only reached environments transitively through `pytest`. (#9)

## [0.5.0] - 2026-06-12

First tagged state of the engine after the bricks / bricks-ai split. Not
released to PyPI: the `bricks` name is taken by an unrelated, filesless
registration, and a rename is pending.

### Added
- Deterministic execution engine: YAML blueprints of typed, pre-tested bricks,
  executed with no LLM in the loop.
- 101 stdlib bricks (pure data transforms).
- Python DSL (`@flow`) compiled to a step list via a compile-time DAG.
- CLI: `run`, `check`, `dry-run`, `store`, and four commands that require the
  separate `bricks_ai` package.
- Blueprint store with SHA-256 fingerprinting.

### Notes
- The engine executes steps sequentially; the DAG is used at compile time only.
- `import-linter` enforces that the engine never imports the AI layer.
