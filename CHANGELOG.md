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

### Fixed
- **A blank unit id is refused (#82).** `bricks run --unit " "` exits 1 with
  `--unit must not be blank (leave it out for 'bench')`, and
  `run_for_unit(..., unit=" ")` returns an `error` outcome instead of writing a
  blank unit into the verdict.

### Added
- **`bricks new brick` / `new blueprint` never overwrite a file (#72).** Both exit 1
  on an existing file, `new brick` rejects invalid or keyword names and names of
  installed bricks, and the blueprint scaffold is now a `measure` step that passes
  `bricks check` and `bricks run` unedited.
- **`bricks.run_for_unit(source, inputs=None, *, unit="bench", registry=None)`
  and `bricks.RunOutcome` (#59).** One public call that runs a blueprint for a
  unit and returns its verdict (`verdict`, `result`, `unit`); a guard stop is
  `fail`, any other `BrickError` or an unreadable blueprint file is `error`, and
  it never raises on a failing run. `bricks run` now goes through it. New module
  `src/bricks/outcome.py`.
- **`blueprints/psu_limits.yaml`: the first test blueprint.** Three `measure`
  steps (`vout`, `iout`, `ripple_pp`) over input values, no hardware; a
  passing and a failing unit are shown in AGENTS.md. (#50)
- **`bricks check-brick`: the ADK check for a brick, plus a function-brick scaffold.**
  `bricks check-brick <pack|module:func> [--json]` tells a brick author whether
  a brick is fit to ship: (1) it loads through its `bricks.packs` entry point,
  or the given `module:func` (a dotted module or a `.py` file path, loaded by
  path like local `auto_discover`, plus one brick's attribute name), and is
  declared with `@brick`; (2) its name does not clash with an installed brick;
  (3) its Meta has a non-empty description, `destructive` set explicitly, and
  no undeclared I/O (new invariant I3, `docs/DECISIONS.md`: "a brick that
  touches the outside world must be a declared capability; Bricks owns no
  I/O"); (4) it runs on a synthesized example input and returns the Mission
  048 contract's output key(s) — the same check `tests/stdlib/test_contracts.py`
  already ran for stdlib bricks, generalised into
  `src/bricks/core/brick_check.py` (`synthesize_inputs`, shared by both).
  Without a `:`, the target is a pack module (e.g. `bricks.stdlib`) and every
  brick it registers is checked. Exit 0 ok, 1 one or more problems (each with
  a `fix` string), 2 the target itself could not be loaded. `--json` prints
  `{"ok", "target", "problems": [{"brick", "check", "fix"}]}`.

  `bricks new brick` now scaffolds what D5/D7 say a brick is — a plain
  `@brick`-decorated function in `bricks_lib/`, not a `BaseBrick` subclass —
  and the scaffold itself passes `check-brick` unedited. ***Upgrading:*** a
  script that parsed the old class-based scaffold (`bricks_lib/<name>.py`
  defining a `BaseBrick` subclass) must update to the new function shape; the
  file path and command are unchanged. (#51, ops#117 CTO ruling 4)

- **`bricks run`: a pass/fail verdict and `--unit`.** `run` takes `--unit ID`
  (default `bench`, never blank), and reports a verdict derived from the
  run — never set by hand (ops `record.md` §2): `fail` if any `measure` step
  returned `pass: false` or a guard stopped the run (`GuardFailedError`),
  `error` if any other `BrickError` ended it, `pass` otherwise. Exit 0 on
  pass, 1 on fail or error, like pytest. Text mode gains a last line,
  `Verdict: PASS (unit bench)` or `Verdict: FAIL (unit SN-2): vout 4.7 V not
  in [4.9, 5.1]`; a `GuardFailedError` no longer tracebacks in text mode. `--json`
  gains `unit`, `verdict` and `measurements` (one row per `measure` step
  that ran); a guard failure is `"ok": true, "verdict": "fail"` (the run did
  what it should), any other error keeps the existing `"ok": false` shape
  and adds `"unit"`/`"verdict": "error"`. New `src/bricks/verdict.py`
  (`derive_verdict`, pure, reads only `measure` steps in a completed
  `ExecutionResult`). Neither `src/bricks/core/engine.py` nor
  `src/bricks/api.py` changed. (#49, ops `record.md` §2 and §3)

- **`measure` brick: one measurement row with a pass verdict.** New stdlib
  brick `measure(name, value, unit, min=None, max=None)` returns
  `{result: {name, value, unit, limits, pass}}`. `limits` holds only the
  bounds given (`{}` if neither), bounds are inclusive, and a non-finite
  `value` (NaN, inf) is `pass: false`. It never raises on a failing value —
  the run continues and a verdict is derived from all rows (a later ticket);
  it raises `ValueError` naming both numbers only when `min > max`. Pure: no
  I/O, clock or random. Lives in the new `measurement` category
  (`src/bricks/stdlib/measurement.py`); the stdlib now ships 102 bricks, 104
  registered with the two DSL builtins. (#48, ops `record.md` R3)

- **CI runs the README Quick Start as printed.** A new `quickstart` job in
  `.github/workflows/ci.yml` (ubuntu and windows) builds the wheel from the
  commit, installs it in a clean venv, and runs the README's Quick Start blocks,
  the Python one and the CLI one, from a temp dir holding a copy of
  `blueprints/`. `dev/quickstart/run_readme.py` reads the commands from
  `README.md`, so the job keeps no copy. A step fails on a non-zero exit, or when
  its output differs from the `#` lines the README shows under it. The CLI block
  runs in bash (Git Bash on Windows), because its JSON is single-quoted. The
  seconds from `pip install` to the first success go into the job summary. The
  README gains three HTML comments, `<!-- quickstart: run -->` and
  `<!-- quickstart: skip -->`, that say which blocks run; the prose is unchanged.
  (#41)

- **`--json` on `bricks run`, `bricks check` and `bricks list`.** With the flag,
  stdout is exactly one JSON document, for success and for failure; warnings,
  and anything a brick prints, go to stderr, and exit codes are unchanged. A
  broken `bricks.config.yaml` is a JSON error too (`ConfigError`). `run` prints
  `{"ok": true, "blueprint", "outputs"}` or
  `{"ok": false, "error": {"type", "message", "step"?, "brick"?}}`; `check`
  prints `{"ok", "file", "errors": [...]}`; `list` prints
  `{"ok": true, "bricks": [...]}` (name, first line of the description, tags,
  category, input_keys, output_keys, destructive, idempotent). An output that
  is not a JSON type is written as its `str()`, a tuple as a list. With
  `--json`, `run` ignores `--verbosity`, and a `BrickError` other than a step
  failure (an unknown brick) is a JSON error instead of a traceback. Without
  the flag the output is byte-identical; `tests/cli/test_json_output.py` checks
  it against output captured before the change. (#40)

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
  uses — and adds the configured paths on top. With no pack installed, the CLI
  prints the install hint and exits 1. `bricks init` still writes `paths: []`.
  **Behaviour change:** before, a local brick in a configured path with the
  same name as a stdlib brick was the one that ran. Now the pack's brick is
  kept, the local one is not used, and the CLI prints
  `Warning: local brick '<name>' has the same name as an installed pack brick;
  the pack version wins and the local one is not used.` to stderr. Rename the
  local brick to use it. (Whether config paths belong in D7 is still #27.)
- **`bricks run -i key=value` passes the value as text when the blueprint
  declares that input as `"str"`.** Before, every value went through
  `json.loads`, so `-i crm_json='[...]'` reached `extract_json_from_str` as a
  list and failed. Inputs not declared `"str"` are still parsed as JSON. The
  README "Quick Start — CLI" now prints a command that runs. A `"str"` input
  given in the old double-quoted form (`-i x='"..."'`) now keeps its quotes:
  the brick gets `"..."`, quotes included, so drop the inner quotes. (#39)

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
