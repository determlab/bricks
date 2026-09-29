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
run: the same blueprint and the same inputs give the same outputs every time,
except where a blueprint uses one of four clock or random bricks (see Side effects).

## Install

bricks is not on PyPI yet. Install from a clone (Python 3.10 to 3.12):

```bash
git clone https://github.com/determlab/bricks.git
cd bricks
pip install -e .
```

## First success

No account, no API key, no config file. Run this from the `bricks` folder; it runs
the example blueprint `blueprints/crm_pipeline.yaml` through the CLI:

```bash
bricks run blueprints/crm_pipeline.yaml -i crm_json='[{"status": "active", "monthly_revenue": 4200}, {"status": "churned", "monthly_revenue": 1800}, {"status": "active", "monthly_revenue": 3100}]'
```

```
Blueprint 'crm_pipeline' completed.
Outputs:
  active_count: 2
  total_active_revenue: 7300
  avg_active_revenue: 3650.0
Verdict: PASS (unit bench)
```

Exit 0. The numbers never change between runs. The CLI loads every installed brick
pack (the stdlib included) with no config: `bricks list` prints
`Registered bricks (104):`. `bricks run` does not validate before it runs
([G8 in docs/DECISIONS.md](docs/DECISIONS.md)), so run `bricks check <file>` first.

The same run through the Python API, which validates, then runs:

```bash
python -c "import json, bricks; rows = [dict(name='Acme', status='active', monthly_revenue=4200), dict(name='Globex', status='churned', monthly_revenue=1800), dict(name='Initech', status='active', monthly_revenue=3100)]; print(bricks.run_blueprint('blueprints/crm_pipeline.yaml', inputs={'crm_json': json.dumps(rows)}).outputs)"
```

prints `{'active_count': 2, 'total_active_revenue': 7300, 'avg_active_revenue': 3650.0}`.

## A test blueprint

`blueprints/psu_limits.yaml` is what a test engineer runs first: three `measure`
steps (`vout` in `4.9..5.1` V, `iout` in `0..1.0` A, `ripple_pp` max 50 mV) against
values you give as inputs — no hardware, no SHAL. A passing unit:

```bash
bricks run blueprints/psu_limits.yaml --unit SN-1 -i vout=5.0 -i iout=0.4 -i ripple_pp=12
```

```
Blueprint 'psu_limits' completed.
Outputs:
  vout: 5.0
  iout: 0.4
  ripple_pp: 12
Verdict: PASS (unit SN-1)
```

Exit 0. A failing unit (`vout` outside its limits):

```bash
bricks run blueprints/psu_limits.yaml --unit SN-2 -i vout=4.7 -i iout=0.4 -i ripple_pp=12
```

```
Blueprint 'psu_limits' completed.
Outputs:
  vout: 4.7
  iout: 0.4
  ripple_pp: 12
Verdict: FAIL (unit SN-2): vout 4.7 V not in [4.9, 5.1]
```

Exit 1. `--json` on either command adds `"verdict"`, `"unit"` and one row per
`measure` step in `"measurements"`, each with its `"pass"`.

## How an agent calls it

From Python:

- `bricks.run_blueprint(path_or_yaml, inputs={...})` — validate, then run.
  Returns a result whose `.outputs` is a dict. A bad blueprint raises
  `BlueprintValidationError`; a failing step raises `BrickExecutionError`, which
  names the step and the brick:
  `Brick 'divide' failed at step 'avg_revenue': Division by zero: b must not be 0`
  (the example above with `inputs={'crm_json': '[]'}`).
- `bricks.run_for_unit(path_or_yaml, inputs={...}, unit="SN-1")` — run for a unit and return a `RunOutcome` (`.verdict.status` is `pass`, `fail` or `error`; `.model_dump_json()` for JSON); never raises on a failing run. It does not validate first, like `bricks run`.
- `bricks.build_default_registry()` — every installed brick (stdlib plus any pack).
- The catalog as data, one dict per brick (name, description, parameters,
  output_keys, destructive, idempotent):

  ```bash
  python -c "import bricks; from bricks.core.schema import registry_schema; s = registry_schema(bricks.build_default_registry()); print(len(s), s[0]['name'])"
  ```

  prints `104 __branch__` (102 stdlib bricks plus 2 DSL builtins).

CLI (`bricks --help` lists all): `run`, `check`, `check-brick`, `dry-run`, `list`,
`init`, `new brick`, `new blueprint`, `new sequence`, `store seed`, `store list`,
`check-env`. `run`, `check`, `check-brick` and `list` take `--json`:
stdout is then exactly one JSON document, for success and for failure, with the
same exit code as without it. Warnings, and anything a brick prints, go to
stderr. The other commands print
text only.

Build a new brick: `bricks new brick <name>` writes `bricks_lib/<name>.py`, then
`bricks check-brick bricks_lib/<name>.py:<name> --json` checks it (or
`bricks check-brick <pack.module> --json` for every brick in a pack). Exit 0: ok.
Exit 1: one or more problems. Exit 2: the target could not be loaded (a missing
file or an import error). The JSON is
`{"ok": false, "target": "...", "problems": [{"brick": "...", "check": "...", "fix": "..."}]}`;
read each `problems[].fix`, edit the brick and run the check again until it exits 0.
Exit 2 adds an `"error"` message and leaves `problems` empty.

`bricks run` also reports a pass/fail verdict and takes `--unit ID` (default
`bench`, never blank), so the same blueprint runs for the next unit without
editing anything: `bricks run <bp> --unit SN-2`. The verdict is derived, never
set by hand — `fail` if any `measure` step returned `pass: false` or a guard
stopped the run, `error` if any other brick error ended it, `pass` otherwise.
Exit 0 on pass, 1 on fail or error — the JSON's `verdict` key says which. In
text mode the last line is `Verdict: PASS (unit bench)` or, on a failing
measurement, `Verdict: FAIL (unit SN-2): vout 4.7 V not in [4.9, 5.1]`.

```bash
bricks run blueprints/crm_pipeline.yaml -i crm_json='[]' --json
```

```
{"ok": false, "error": {"type": "BrickExecutionError", "message": "Brick 'divide' failed at step 'avg_revenue': Division by zero: b must not be 0", "step": "avg_revenue", "brick": "divide"}, "unit": "bench", "verdict": "error"}
```

Exit 1. With the three-row input from First success it prints
`{"ok": true, "blueprint": "crm_pipeline", "unit": "bench", "verdict": "pass", "measurements": [], "outputs": {"active_count": 2, "total_active_revenue": 7300, "avg_active_revenue": 3650.0}}`.
`measurements` is one row per `measure` step that ran (`{"step", "name", "value",
"unit", "limits", "pass"}`), empty when the blueprint has none. A guard that
stops the run is `{"ok": true, "verdict": "fail", "measurements": [], "outputs": {}, ...}`
— the run did what it should; a `BrickError` other than a guard keeps the
`"ok": false` shape above and adds `"unit"` and `"verdict": "error"`.
An output value that is not a JSON type (a date, a set, `NaN`) is written as its
`str()`; a tuple becomes a list. `bricks check blueprints/crm_pipeline.yaml --json`
prints `{"ok": true, "file": "blueprints/crm_pipeline.yaml", "errors": []}`; when
not valid, `ok` is false and `errors` lists each problem. `bricks list --json`
prints `{"ok": true, "bricks": [...]}`, one entry per brick with `name`,
`description` (first line only), `tags`, `category`, `input_keys`, `output_keys`,
`destructive` and `idempotent`.

With `auto_discover: true`, the `paths` in `bricks.config.yaml` add local
bricks on top of the packs. A local brick with a pack brick's name is not used, and
the CLI prints a warning naming it to stderr. `compose`, `demo`, `serve` and
`playground` (`playground run`) need the separate `bricks-ai` package and an LLM.
`bricks serve` (the MCP server) is one of them: without it, it exits 1 with
`Error: MCP features require the 'mcp' package.` There is no MCP server in this
package.

## Side effects

- `run_blueprint` runs bricks in your process. The stdlib bricks make no file,
  network or process calls.
- Four stdlib bricks read the clock or random (`now_timestamp`, `days_until`,
  `generate_uuid`, `random_string`), so a blueprint that uses one is not
  reproducible ([G1 in docs/DECISIONS.md](docs/DECISIONS.md)).
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
