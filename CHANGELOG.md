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
  is recovered by a single tier-2 search. The cost of the full listing is a mean
  of 3.00 same-keyword rivals beside the right answer against 0.37 (precision,
  0.0099 against 0.0714, is by the same construction as the hit-rate — every
  task has one expected brick, so it is exactly 1/listing-size, not a discovered
  number). The measurement has no model in it, so it reports what a caller is
  *shown*, not what a model would *pick*.

  Test-only: no engine behaviour changed. Regenerate the baseline with
  `BRICKS_UPDATE_BASELINE=1 python -m pytest tests/core/test_selector_measurement.py`.
  (#31, `tool-set.md` R6)

- **A blueprint run twice gives byte-identical output (D1).**
  `tests/core/test_determinism.py` runs a small `__for_each__` blueprint
  twice with the same inputs and asserts the two `ExecutionResult.outputs`
  are equal and render to the same bytes. A second test runs a blueprint that
  calls `now_timestamp` against a controlled clock and asserts the two runs
  differ, so the comparison is shown to be able to fail (G1). This closes G3.
  Test-only: no engine behaviour changed. (#32)

### Changed
- **`CatalogConfig.common_set` ships populated.** It defaulted to empty; it now
  holds the 14 bricks `block-set.md` keeps visible (`sort_dict_list`,
  `map_values`, `group_by_key`, `calculate_aggregates`, `extract_json_from_str`,
  `select_dict_keys`, `merge_dictionaries`, `add_days`, `date_diff`,
  `compare_values`, `is_not_empty`, `unique_values`, `round_number`,
  `percentage`), exposed as `bricks.core.config.DEFAULT_COMMON_SET`. A caller
  that builds `TieredCatalog(registry, common_set=CatalogConfig().common_set)`
  now lists those 14; `TieredCatalog(registry)` alone still lists nothing, and
  no composer is wired to the default yet (G10). The registry is unchanged: every other brick is still reachable
  through tier-2 search. (#35, `tool-set.md` R3, D15)

  ***Upgrading:*** a caller that relied on the default config to list a
  different set (the full registry, or nothing) must now pass a config with its
  own `catalog.common_set` — in `bricks.config.yaml`, or
  `CatalogConfig(common_set=[...])`.

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
- **The CLI loads the `bricks.packs` entry point.** `bricks run`, `check`,
  `dry-run`, `list` and `compose` built their registry only from the paths in
  `bricks.config.yaml`, so from a fresh clone they saw no stdlib bricks at all.
  `_setup_registry` now starts from `build_default_registry()` — every
  installed pack plus the DSL builtins, the same registry `run_blueprint()`
  uses — and adds the configured paths on top. Packs load first, so on a name
  clash the pack's brick is kept and the path's brick is skipped. With no pack
  installed, the CLI prints the install hint and exits 1. `bricks init` still
  writes `paths: []`.
- **`bricks run -i key=value` passes the value as text when the blueprint
  declares that input as `"str"`.** Before, every value went through
  `json.loads`, so `-i crm_json='[...]'` reached `extract_json_from_str` as a
  list and failed. Inputs not declared `"str"` are still parsed as JSON. The
  README "Quick Start — CLI" now prints a command that runs. (#39)

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
