"""Typer CLI application with all Bricks commands."""

from __future__ import annotations

import contextlib
import importlib
import importlib.util
import json
import math
import os
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import typer
from pydantic import ValidationError

from bricks.api import build_default_registry
from bricks.cli.check_env import check_env as _check_env_fn
from bricks.core.brick_check import CheckTarget, Problem, run_checks
from bricks.core.config import BricksConfig, ConfigLoader
from bricks.core.discovery import BrickDiscovery
from bricks.core.exceptions import (
    BlueprintValidationError,
    BrickExecutionError,
    ConfigError,
    GuardFailedError,
    YamlLoadError,
)
from bricks.core.loader import BlueprintLoader
from bricks.core.models import Verbosity
from bricks.core.registry import BrickRegistry
from bricks.core.schema import brick_schema
from bricks.core.validation import BlueprintValidator
from bricks.errors import BricksConfigError
from bricks.outcome import run_for_unit

app = typer.Typer(
    name="bricks",
    help="Bricks - Deterministic sequencing engine for typed Python building blocks.",
    no_args_is_help=True,
)

new_app = typer.Typer(help="Scaffold new Bricks components.")
app.add_typer(new_app, name="new")

_JSON_HELP = "Print one JSON document to stdout instead of text."


def _jsonable(value: Any) -> Any:
    """Turn *value* into something ``json.dumps`` writes as strict JSON.

    Dicts (keys as ``str``), lists and tuples (as lists) are walked; ``str``,
    ``int``, ``bool``, ``None`` and finite ``float`` pass through. Anything else,
    a ``NaN`` or infinite float included, is written as ``str(value)``.
    """
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    return str(value)


def _emit_json(doc: dict[str, Any]) -> None:
    """Write *doc* to stdout as one JSON document."""
    typer.echo(json.dumps(_jsonable(doc), allow_nan=False))


def _json_error(error_type: str, message: str, **extra: str) -> dict[str, Any]:
    """The ``--json`` failure shape shared by ``run`` and ``list``."""
    return {"ok": False, "error": {"type": error_type, "message": message, **extra}}


def _emit_config_error(error_type: str, message: str) -> None:
    """``--json`` report for a config or registry that cannot be built (``run`` and ``list``)."""
    _emit_json(_json_error(error_type, message))


def _setup_registry(
    config_dir: Path | None = None,
    on_error: Callable[[str, str], None] | None = None,
) -> tuple[BrickRegistry, BricksConfig]:
    """Load config and build the registry the CLI runs against.

    Starts from the Python API's default registry — every installed
    ``bricks.packs`` pack (the stdlib included) plus DSL builtins — then adds
    the bricks found in ``config.registry.paths`` when ``auto_discover`` is on.
    On a name clash the pack's brick is kept, the path's brick is skipped, and
    a warning naming the brick goes to stderr.

    Args:
        config_dir: Directory to search for bricks.config.yaml. Defaults to cwd.
        on_error: ``--json`` passes one. It is called with the error type and
            message when the config or the registry cannot be built, and exit
            is 1. While it is set, anything a brick module prints while loading
            goes to stderr, so stdout carries the JSON alone. Without it, the
            output is as before: ``Error:`` on stderr for no packs, and a bad
            config raises.

    Returns:
        A tuple of (registry, config).
    """
    guard = contextlib.redirect_stdout(sys.stderr) if on_error is not None else contextlib.nullcontext()
    try:
        with guard:
            return _build_registry(config_dir)
    except BricksConfigError as exc:
        if on_error is not None:
            on_error(type(exc).__name__, str(exc))
        else:
            typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    except (ConfigError, ValidationError) as exc:
        if on_error is None:
            raise
        on_error(type(exc).__name__, str(exc))
        raise typer.Exit(code=1) from exc


def _build_registry(config_dir: Path | None) -> tuple[BrickRegistry, BricksConfig]:
    """The body of :func:`_setup_registry`: load the config, then build the registry."""
    loader = ConfigLoader()
    config = loader.load(directory=config_dir)
    registry = build_default_registry()
    if config.registry.auto_discover:
        local = BrickRegistry()
        discovery = BrickDiscovery(registry=local)
        for path_str in config.registry.paths:
            p = Path(path_str)
            if not p.is_absolute():
                p = (config_dir or Path.cwd()) / p
            if p.is_dir():
                discovery.discover_package(p)
            elif p.suffix == ".py" and p.exists():
                discovery.discover_path(p)
        for name, _ in local.list_all():
            if registry.has(name):
                typer.echo(
                    f"Warning: local brick {name!r} has the same name as an installed pack brick; "
                    "the pack version wins and the local one is not used.",
                    err=True,
                )
                continue
            callable_, meta = local.get(name)
            registry.register(name, callable_, meta)
    return registry, config


@app.command()
def init() -> None:
    """Scaffold a new Bricks project in the current directory."""
    config_file = Path.cwd() / "bricks.config.yaml"
    if config_file.exists():
        typer.echo("Error: bricks.config.yaml already exists.", err=True)
        raise typer.Exit(code=1)

    config_content = """version: "1"
registry:
  auto_discover: false
  paths: []
sequences:
  base_dir: "blueprints/"
ai:
  model: "claude-haiku-4-5-20251001"
  max_tokens: 4096
"""
    config_file.write_text(config_content)
    blueprints_dir = Path.cwd() / "blueprints"
    blueprints_dir.mkdir(exist_ok=True)
    bricks_lib = Path.cwd() / "bricks_lib"
    bricks_lib.mkdir(exist_ok=True)
    (bricks_lib / "__init__.py").write_text("")
    typer.echo("Created bricks.config.yaml")
    typer.echo("Created blueprints/")
    typer.echo("Created bricks_lib/")
    typer.echo("Bricks project initialised.")


@new_app.command("brick")
def new_brick(
    name: str = typer.Argument(..., help="Name of the brick (snake_case)."),
) -> None:
    """Scaffold a new Brick: a plain function decorated with @brick, in a pack (D5, D7).

    Writes ``bricks_lib/<name>.py`` with a small working brick — no base
    class, matching how every stdlib brick is written. Check it with
    ``bricks check-brick <path>:<name> --json`` (printed below) and edit from
    there; the scaffold itself already passes every check.
    """
    snake_name = name.lower().replace("-", "_").replace(" ", "_")

    output_path = Path.cwd() / "bricks_lib" / f"{snake_name}.py"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    content = f'''"""Brick: {snake_name}."""

from __future__ import annotations

from bricks.core.brick import brick


@brick(
    tags=[],
    category="general",
    destructive=False,
    idempotent=True,
    description="Echo value unchanged. Returns {{result: value}}.",
)
def {snake_name}(value: str) -> dict[str, str]:
    """Echo value unchanged — replace this with real logic.

    Args:
        value: Input value.

    Returns:
        dict with key ``result``.
    """
    return {{"result": value}}
'''
    output_path.write_text(content)
    try:
        rel_path = output_path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        rel_path = str(output_path)
    typer.echo(f"Created {output_path}")
    typer.echo(f"Check it: bricks check-brick {rel_path}:{snake_name} --json")
    typer.echo(
        "To ship it as an installed pack instead of a local bricks_lib/ file: "
        "give it a register(registry) function (see src/bricks/stdlib/__init__.py) "
        'and add to pyproject.toml: [project.entry-points."bricks.packs"] '
        f'{snake_name}_pack = "bricks_lib"'
    )


@new_app.command("blueprint")
def new_blueprint(name: str = typer.Argument(..., help="Name of the blueprint.")) -> None:
    """Scaffold a new YAML blueprint file."""
    snake_name = name.lower().replace("-", "_").replace(" ", "_")

    loader = ConfigLoader()
    config = loader.load()
    bp_dir = Path.cwd() / config.sequences.base_dir
    bp_dir.mkdir(parents=True, exist_ok=True)

    output_path = bp_dir / f"{snake_name}.yaml"
    content = f"""name: {snake_name}
description: ""
inputs:
  # input_name: "type"
steps:
  - name: step_1
    brick: my_brick
    params: {{}}
    save_as: step_1_result
outputs_map:
  result: "${{step_1_result}}"
"""
    output_path.write_text(content)
    typer.echo(f"Created {output_path}")


@new_app.command("sequence")
def new_sequence(name: str = typer.Argument(..., help="Name of the sequence.")) -> None:
    """Scaffold a new YAML sequence file (alias for 'new blueprint')."""
    new_blueprint(name)


@app.command()
def check(
    file: str = typer.Argument(..., help="Path to blueprint YAML file."),
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP),
) -> None:
    """Validate a blueprint YAML file (lint without executing).

    With --json: {"ok", "file", "errors": [str, ...]}; exit 1 when not ok.
    """
    path = Path(file)

    def fail_json(*errors: str) -> None:
        _emit_json({"ok": False, "file": file, "errors": list(errors)})

    if not path.exists():
        if json_output:
            fail_json(f"File not found: {path}")
        else:
            typer.echo(f"Error: File not found: {path}", err=True)
        raise typer.Exit(code=1)

    bp_loader = BlueprintLoader()
    try:
        blueprint = bp_loader.load_file(path)
    except YamlLoadError as exc:
        if json_output:
            fail_json(f"Error loading YAML: {exc}")
        else:
            typer.echo(f"Error loading YAML: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    registry, _ = _setup_registry(on_error=(lambda _type, msg: fail_json(msg)) if json_output else None)
    validator = BlueprintValidator(registry=registry)

    try:
        validator.validate(blueprint)
    except BlueprintValidationError as exc:
        if json_output:
            fail_json(*(exc.errors or [str(exc)]))
            raise typer.Exit(code=1) from exc
        typer.echo(f"Validation errors in {path}:", err=True)
        if exc.errors:
            for error in exc.errors:
                typer.echo(f"  - {error}", err=True)
        raise typer.Exit(code=1) from exc
    if json_output:
        _emit_json({"ok": True, "file": file, "errors": []})
    else:
        typer.echo(f"valid: {path}")


class CheckBrickLoadError(Exception):
    """The check-brick target itself could not be loaded — exit code 2."""


def _load_check_brick_module(module_ref: str) -> ModuleType:
    """Import *module_ref*: a dotted module path, or a ``.py`` file path.

    A path is loaded directly from disk (the same technique
    :class:`~bricks.core.discovery.BrickDiscovery` uses for a local file) so
    it needs no package or ``sys.path`` entry — the scaffold ``bricks new
    brick`` writes into ``bricks_lib/`` can be checked in place.

    Args:
        module_ref: Dotted import path (``bricks.stdlib``) or a path to a
            ``.py`` file (``bricks_lib/demo.py``).

    Returns:
        The imported module.

    Raises:
        CheckBrickLoadError: The module cannot be found or imported.
    """
    looks_like_path = module_ref.endswith(".py") or "/" in module_ref or "\\" in module_ref
    if looks_like_path:
        path = Path(module_ref)
        if not path.exists():
            raise CheckBrickLoadError(f"No such file: {path}")
        spec = importlib.util.spec_from_file_location(f"_check_brick_{path.stem}", path)
        if spec is None or spec.loader is None:
            raise CheckBrickLoadError(f"Cannot load spec for {path}")
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            raise CheckBrickLoadError(f"Error importing {path}: {exc}") from exc
        return module
    try:
        return importlib.import_module(module_ref)
    except Exception as exc:
        raise CheckBrickLoadError(f"Error importing {module_ref!r}: {exc}") from exc


def _resolve_check_targets(target: str) -> list[CheckTarget]:
    """Resolve *target* (a pack module, or ``module:func``) to bricks to check.

    Args:
        target: ``"module:func"`` checks the one brick ``func`` in ``module``
            (a dotted path or a ``.py`` file). Without a ``:``, *target* is a
            pack module (dotted path, e.g. ``bricks.stdlib``) with a
            ``register(registry)`` function — every brick it registers is
            checked (D7: that function is how a pack arrives).

    Returns:
        One :class:`~bricks.core.brick_check.CheckTarget` per brick to check.
        A ``module:func`` target that doesn't name a declared brick still
        returns one entry, carrying the check-1 problem — that is a fixable
        exit-1 finding, not a load failure.

    Raises:
        CheckBrickLoadError: *target* itself could not be loaded at all.
    """
    if ":" in target:
        module_ref, _sep, func_name = target.rpartition(":")
        module = _load_check_brick_module(module_ref)
        obj = getattr(module, func_name, None)
        if obj is None:
            return [
                CheckTarget(
                    name=func_name,
                    callable_=None,
                    meta=None,
                    problems=[
                        Problem(
                            brick=func_name,
                            check="brick.exists",
                            fix=f"Define `{func_name}` in {module_ref} — no such attribute.",
                        )
                    ],
                )
            ]
        if not callable(obj) or not hasattr(obj, "__brick_meta__"):
            return [
                CheckTarget(
                    name=func_name,
                    callable_=None,
                    meta=None,
                    problems=[
                        Problem(
                            brick=func_name,
                            check="brick.declared",
                            fix=f"Decorate `{func_name}` with @brick(...) from bricks.core.brick "
                            "so it registers as a brick.",
                        )
                    ],
                )
            ]
        return [CheckTarget(name=func_name, callable_=obj, meta=obj.__brick_meta__, problems=[])]

    module = _load_check_brick_module(target)
    register_fn = getattr(module, "register", None)
    if register_fn is None or not callable(register_fn):
        raise CheckBrickLoadError(f"{target!r} has no register(registry) function — it is not a brick pack.")
    local = BrickRegistry()
    try:
        register_fn(local)
    except Exception as exc:
        raise CheckBrickLoadError(f"{target!r}.register() raised {type(exc).__name__}: {exc}") from exc
    targets = [
        CheckTarget(name=name, callable_=local.get(name)[0], meta=meta, problems=[]) for name, meta in local.list_all()
    ]
    if not targets:
        raise CheckBrickLoadError(f"{target!r} registered no bricks.")
    return targets


@app.command(name="check-brick")
def check_brick(
    target: str = typer.Argument(
        ...,
        help="A pack module (dotted, e.g. 'bricks.stdlib') to check every brick in it, or "
        "'module:func' — a dotted module or .py file path, plus one brick's attribute name.",
    ),
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP),
) -> None:
    """Check whether a brick — or every brick in a pack — is fit to ship (ops#117 ruling 4).

    Per brick: (1) it loads through its ``bricks.packs`` entry point, or the
    given ``module:func``, and is declared with ``@brick``; (2) its name
    does not clash with an installed brick; (3) its Meta has a non-empty
    description, ``destructive`` set explicitly, and no undeclared I/O (I3:
    a brick that touches the outside world must be a declared capability —
    Bricks owns no I/O); (4) it runs on a synthesized example input and
    returns the Mission 048 contract's output key(s).

    Exit 0: ok. Exit 1: one or more problems, each with a ``fix``. Exit 2:
    *target* itself could not be loaded (a bad pack or an import error). With
    --json: {"ok", "target", "problems": [{"brick", "check", "fix"}]}; an
    exit-2 failure adds "error" (a message) and "problems" stays empty.
    """
    try:
        targets = _resolve_check_targets(target)
    except CheckBrickLoadError as exc:
        if json_output:
            _emit_json({"ok": False, "target": target, "problems": [], "error": str(exc)})
        else:
            typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    try:
        reference_registry = build_default_registry()
    except BricksConfigError as exc:
        if json_output:
            _emit_json({"ok": False, "target": target, "problems": [], "error": str(exc)})
        else:
            typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    problems: list[dict[str, str]] = []
    for one_target in targets:
        problems.extend(p.as_dict() for p in run_checks(one_target, reference_registry))

    ok = not problems
    if json_output:
        _emit_json({"ok": ok, "target": target, "problems": problems})
    elif ok:
        count = len(targets)
        typer.echo(f"ok: {target} ({count} brick{'s' if count != 1 else ''} checked)")
    else:
        typer.echo(f"{len(problems)} problem(s) in {target}:")
        for p in problems:
            typer.echo(f"  - [{p['brick']}] {p['check']}: {p['fix']}")

    if not ok:
        raise typer.Exit(code=1)


@app.command()
def run(
    sequence: str = typer.Argument(..., help="Path to blueprint YAML file."),
    input_: list[str] = typer.Option(  # noqa: B008
        [], "--input", "-i", help="Input values as key=value."
    ),
    unit: str = typer.Option("bench", "--unit", help="Unit under test. Carried through to the verdict, never blank."),
    verbosity: Verbosity = typer.Option(  # noqa: B008
        Verbosity.MINIMAL, "--verbosity", "-v", help="Output detail level (minimal/standard/full)."
    ),
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP + " Ignores --verbosity."),
) -> None:
    """Execute a blueprint and report a pass/fail verdict.

    The verdict is derived, never set by hand: ``fail`` if any ``measure``
    step returned ``pass: false`` or a guard stopped the run, ``error`` if
    any other brick error ended it, ``pass`` otherwise. Exit 0 on pass, 1 on
    fail or error.

    With --json: {"ok": true, "blueprint", "unit", "verdict", "measurements",
    "outputs"}. A guard failure is {"ok": true, "verdict": "fail", ...} — the
    run did what it should. Any other failure keeps today's shape,
    {"ok": false, "error": {"type", "message", "step"?, "brick"?}}, and adds
    "unit" and "verdict".
    """
    path = Path(sequence)
    if not path.exists():
        if json_output:
            _emit_json(_json_error("FileNotFoundError", f"Blueprint file not found: {path}"))
        else:
            typer.echo(f"Error: Blueprint file not found: {path}", err=True)
        raise typer.Exit(code=1)

    bp_loader = BlueprintLoader()
    try:
        bp_def = bp_loader.load_file(path)
    except YamlLoadError as exc:
        if json_output:
            _emit_json(_json_error("YamlLoadError", str(exc)))
        else:
            typer.echo(f"Error loading YAML: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if not unit.strip():
        blank_msg = "--unit must not be blank (leave it out for 'bench')"
        if json_output:
            _emit_json(_json_error("InvalidInputError", blank_msg))
        else:
            typer.echo(f"Error: {blank_msg}", err=True)
        raise typer.Exit(code=1)

    inputs: dict[str, object] = {}
    for item in input_:
        if "=" not in item:
            if json_output:
                _emit_json(_json_error("InvalidInputError", f"Invalid input format {item!r}. Use key=value."))
            else:
                typer.echo(f"Error: Invalid input format {item!r}. Use key=value.", err=True)
            raise typer.Exit(code=1)
        k, v = item.split("=", 1)
        # An input the blueprint declares as "str" is passed as typed, so
        # crm_json='[...]' reaches the brick as text, the same as the Python API.
        if bp_def.inputs.get(k) == "str":
            inputs[k] = v
            continue
        try:
            inputs[k] = json.loads(v)
        except json.JSONDecodeError:
            inputs[k] = v

    registry, _ = _setup_registry(on_error=_emit_config_error if json_output else None)

    # The verdict reads each `measure` step's output, so run_for_unit runs at
    # least at STANDARD; --verbosity still controls what gets printed below.
    # What a brick prints goes to stderr under --json, so stdout carries the
    # JSON alone.
    if json_output:
        with contextlib.redirect_stdout(sys.stderr):
            outcome = run_for_unit(bp_def, inputs or None, unit=unit, registry=registry)
    else:
        outcome = run_for_unit(bp_def, inputs or None, unit=unit, registry=registry, verbosity=verbosity)
    verdict = outcome.verdict
    exec_result = outcome.result
    # Not `exc`: mypy treats that name as still bound (then deleted) by an
    # earlier `except ... as exc:` in this same function, and flags any
    # later plain assignment to it as "reading a deleted variable" (bricks#62).
    run_error = outcome.error

    if json_output:
        if isinstance(run_error, GuardFailedError):
            # A guard failure is a verdict, not a JSON error: `ok: true` (the
            # run did what it should).
            _emit_json(
                {
                    "ok": True,
                    "blueprint": bp_def.name,
                    "unit": unit,
                    "verdict": verdict.status,
                    "measurements": verdict.measurements,
                    "outputs": {},
                }
            )
            raise typer.Exit(code=1)
        if exec_result is None:
            # Any other BrickError keeps the `ok: false` shape plus "unit" and "verdict".
            if isinstance(run_error, BrickExecutionError):
                doc = _json_error(
                    type(run_error).__name__, str(run_error), step=run_error.step_name, brick=run_error.brick_name
                )
            else:
                doc = _json_error(type(run_error).__name__, str(run_error))
            _emit_json({**doc, "unit": unit, "verdict": verdict.status})
            raise typer.Exit(code=1)
        _emit_json(
            {
                "ok": True,
                "blueprint": bp_def.name,
                "unit": unit,
                "verdict": verdict.status,
                "measurements": verdict.measurements,
                "outputs": exec_result.outputs,
            }
        )
        if verdict.status != "pass":
            raise typer.Exit(code=1)
        return

    if isinstance(run_error, GuardFailedError):
        typer.echo(f"Verdict: FAIL (unit {unit}): {verdict.detail}")
        raise typer.Exit(code=1)
    if exec_result is None:
        typer.echo(f"Execution error: {run_error}", err=True)
        typer.echo(f"Verdict: ERROR (unit {unit}): {verdict.detail}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Blueprint {bp_def.name!r} completed.")
    if exec_result.outputs:
        typer.echo("Outputs:")
        for k, v in exec_result.outputs.items():
            typer.echo(f"  {k}: {v!r}")

    if verbosity in (Verbosity.STANDARD, Verbosity.FULL) and exec_result.steps:
        typer.echo("Steps:")
        for s in exec_result.steps:
            line = f"  [{s.step_name}] {s.brick_name}"
            if verbosity == Verbosity.FULL:
                line += f" ({s.duration_ms:.1f}ms)"
            typer.echo(line)
            if s.outputs:
                typer.echo(f"    outputs: {s.outputs!r}")
            if verbosity == Verbosity.FULL and s.inputs:
                typer.echo(f"    inputs:  {s.inputs!r}")

    if verbosity == Verbosity.FULL:
        typer.echo(f"Total: {exec_result.total_duration_ms:.1f}ms")

    if verdict.status == "pass":
        typer.echo(f"Verdict: PASS (unit {unit})")
    else:
        typer.echo(f"Verdict: FAIL (unit {unit}): {verdict.detail}")
        raise typer.Exit(code=1)


@app.command(name="dry-run")
def dry_run(
    sequence: str = typer.Argument(..., help="Path to blueprint YAML file."),
) -> None:
    """Validate a blueprint without executing (dry run)."""
    path = Path(sequence)
    if not path.exists():
        typer.echo(f"Error: Blueprint file not found: {path}", err=True)
        raise typer.Exit(code=1)

    bp_loader = BlueprintLoader()
    try:
        bp_def = bp_loader.load_file(path)
    except YamlLoadError as exc:
        typer.echo(f"Error loading YAML: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    registry, _ = _setup_registry()
    validator = BlueprintValidator(registry=registry)

    try:
        validator.validate(bp_def)
        typer.echo(f"Blueprint {bp_def.name!r} is valid (dry-run passed).")
    except BlueprintValidationError as exc:
        typer.echo("Validation errors:", err=True)
        if exc.errors:
            for error in exc.errors:
                typer.echo(f"  - {error}", err=True)
        raise typer.Exit(code=1) from exc


@app.command(name="list")
def list_bricks(
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP),
) -> None:
    """List all available Bricks in the registry.

    With --json: {"ok": true, "bricks": [{"name", "description" (first line),
    "tags", "category", "destructive", "idempotent", "input_keys", "output_keys"}]}.
    """
    registry, _ = _setup_registry(on_error=_emit_config_error if json_output else None)
    all_bricks = registry.list_all()

    if json_output:
        entries = []
        for name, _meta in all_bricks:
            schema = brick_schema(name, registry)
            del schema["parameters"]
            lines = str(schema["description"]).strip().splitlines()
            schema["description"] = lines[0] if lines else ""
            entries.append(schema)
        _emit_json({"ok": True, "bricks": entries})
        return

    if not all_bricks:
        typer.echo("No bricks registered. Check your bricks.config.yaml registry paths.")
        return

    typer.echo(f"Registered bricks ({len(all_bricks)}):")
    for name, meta in all_bricks:
        tags_str = f" [{', '.join(meta.tags)}]" if meta.tags else ""
        destructive_str = " [DESTRUCTIVE]" if meta.destructive else ""
        desc_str = f" - {meta.description}" if meta.description else ""
        typer.echo(f"  {name}{tags_str}{destructive_str}{desc_str}")


@app.command(name="check-env")
def check_env() -> None:
    """Diagnose the local environment (Python version, litellm, Windows path limits)."""
    _check_env_fn()


store_app = typer.Typer(help="Blueprint store management.")
app.add_typer(store_app, name="store")


@store_app.command("seed")
def store_seed(
    directory: str = typer.Argument(..., help="Directory containing YAML blueprint files."),
    store_path: str = typer.Option(
        "./blueprint_store",
        "--store",
        "-s",
        help="File store path.",
    ),
) -> None:
    """Load YAML blueprints from a directory into the file store."""
    from datetime import datetime, timezone  # noqa: PLC0415

    from bricks.core.exceptions import DuplicateBlueprintError  # noqa: PLC0415
    from bricks.core.loader import BlueprintLoader  # noqa: PLC0415
    from bricks.store.blueprint_store import FileBlueprintStore  # noqa: PLC0415
    from bricks.store.models import StoredBlueprint  # noqa: PLC0415

    bp_dir = Path(directory)
    if not bp_dir.is_dir():
        typer.echo(f"Error: Directory not found: {bp_dir}", err=True)
        raise typer.Exit(code=1)

    store = FileBlueprintStore(store_path)
    loader = BlueprintLoader()
    loaded = 0
    skipped = 0

    for yaml_path in sorted(bp_dir.glob("*.yaml")):
        try:
            bp = loader.load_file(yaml_path)
            yaml_text = yaml_path.read_text(encoding="utf-8")
            stored = StoredBlueprint(
                name=bp.name,
                yaml=yaml_text,
                fingerprints=[],
                created_at=datetime.now(timezone.utc),
            )
            try:
                store.save(stored)
                typer.echo(f"  Loaded: {bp.name}")
            except DuplicateBlueprintError:
                store.delete(bp.name)
                store.save(stored)
                typer.echo(f"  Updated: {bp.name} (already existed)")
            loaded += 1
        except Exception as exc:
            typer.echo(f"  Skipped {yaml_path.name}: {exc}", err=True)
            skipped += 1

    typer.echo(f"\nDone: {loaded} loaded, {skipped} skipped.")


@store_app.command("list")
def store_list(
    store_path: str = typer.Option(
        "./blueprint_store",
        "--store",
        "-s",
        help="File store path.",
    ),
) -> None:
    """List blueprints in the file store."""
    from bricks.store.blueprint_store import FileBlueprintStore  # noqa: PLC0415

    store = FileBlueprintStore(store_path)
    blueprints = store.list_all()
    if not blueprints:
        typer.echo("No blueprints in store.")
        return
    typer.echo(f"Blueprints in store ({len(blueprints)}):")
    for bp in blueprints:
        typer.echo(f"  {bp.name} (used {bp.use_count}x)")


@app.command()
def compose(
    intent: str = typer.Argument(..., help="Natural language description."),
) -> None:
    """AI-compose a blueprint from a natural language description."""
    import importlib.util  # noqa: PLC0415

    # litellm itself is imported lazily inside LiteLLMProvider.complete(), so
    # importing the provider module succeeds even without the [ai] extra —
    # check availability explicitly to fail fast before prompting for a key.
    if importlib.util.find_spec("litellm") is None:
        typer.echo("Error: AI features require the 'litellm' package.", err=True)
        typer.echo('Install with: pip install "bricks-ai[ai]"', err=True)
        raise typer.Exit(code=1)

    try:
        from bricks_ai.composer import BlueprintComposer  # noqa: PLC0415
        from bricks_ai.llm.litellm_provider import LiteLLMProvider  # noqa: PLC0415
    except ImportError as exc:
        typer.echo("Error: AI features require the 'litellm' package.", err=True)
        typer.echo('Install with: pip install "bricks-ai[ai]"', err=True)
        raise typer.Exit(code=1) from exc

    api_key = os.environ.get("ANTHROPIC_API_KEY") or typer.prompt("Anthropic API key", hide_input=True)
    registry, _ = _setup_registry()
    composer = BlueprintComposer(provider=LiteLLMProvider(api_key=api_key))

    try:
        from bricks_ai.composer import ComposerError  # noqa: PLC0415

        result = composer.compose(intent, registry)
        typer.echo(f"Valid: {result.is_valid}")
        typer.echo(f"API calls: {result.api_calls} | Tokens: {result.total_tokens}")
        if result.is_valid:
            typer.echo(f"\n{result.blueprint_yaml}")
        else:
            typer.echo(f"Validation errors: {result.validation_errors}", err=True)
    except ComposerError as exc:
        typer.echo(f"Composition failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def demo(
    act: int = typer.Option(0, "--act", help="Run only act 1, 2, or 3. Default 0 = all acts."),
    model: str = typer.Option("claude-haiku-4-5", "--model", help="LiteLLM model string."),
    provider_name: str = typer.Option("", "--provider", help="Provider override: 'claudecode' (no API key needed)."),
) -> None:
    """Interactive 3-act demo: simplicity -> correctness -> savings."""
    try:
        from bricks_ai.demo.runner import DemoRunner  # noqa: PLC0415
        from bricks_ai.llm.base import LLMProvider  # noqa: PLC0415
    except ImportError as exc:
        typer.echo("Error: the demo requires the AI layer.", err=True)
        typer.echo('Install with: pip install "bricks-ai[ai]"', err=True)
        raise typer.Exit(code=1) from exc

    resolved_provider: LLMProvider | None = None

    if provider_name == "claudecode":
        try:
            from bricks_ai.providers.claudecode.provider import (  # noqa: PLC0415
                ClaudeCodeProvider,
            )

            resolved_provider = ClaudeCodeProvider()
        except ImportError:
            typer.echo(
                "ClaudeCodeProvider not installed. Run: pip install -e packages/provider-claudecode --no-deps",
                err=True,
            )
            raise typer.Exit(code=1) from None
    elif os.getenv("BRICKS_MODEL") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"):
        try:
            from bricks_ai.llm.litellm_provider import LiteLLMProvider  # noqa: PLC0415
        except ImportError as exc:
            typer.echo("Error: live demo mode requires the 'litellm' package.", err=True)
            typer.echo('Install with: pip install "bricks-ai[ai]"', err=True)
            raise typer.Exit(code=1) from exc

        resolved_model = os.getenv("BRICKS_MODEL", model)
        resolved_provider = LiteLLMProvider(model=resolved_model)

    runner = DemoRunner(provider=resolved_provider)
    if act == 0:
        runner.run_all()
    elif act == 1:
        runner.run_act1()
    elif act == 2:
        runner.run_act2()
    elif act == 3:
        runner.run_act3()
    else:
        typer.echo(f"Invalid act {act!r}. Choose 1, 2, or 3.", err=True)
        raise typer.Exit(code=1)


@app.command()
def serve(
    config: str | None = typer.Option(None, "--config", "-c", help="Path to agent.yaml config file."),
    model: str = typer.Option("claude-haiku-4-5", "--model", "-m", help="LiteLLM model string."),
) -> None:
    """Start the Bricks MCP server on stdio transport."""
    import asyncio  # noqa: PLC0415

    try:
        from bricks_ai import Bricks  # noqa: PLC0415
        from bricks_ai.mcp.server import run_mcp_server  # noqa: PLC0415
    except ImportError as exc:
        typer.echo("Error: MCP features require the 'mcp' package.", err=True)
        typer.echo('Install with: pip install "bricks-ai[mcp,ai]"', err=True)
        raise typer.Exit(code=1) from exc

    typer.echo("Starting Bricks MCP server (stdio)...", err=True)
    if config:
        engine = Bricks.from_config(config)
        typer.echo(f"Loaded config: {config}", err=True)
    else:
        engine = Bricks.default(model=model, store_backend="file", store_path="~/.bricks/blueprints")
        typer.echo(f"Using model: {model}", err=True)
    typer.echo("Server ready. Waiting for MCP client...", err=True)

    asyncio.run(run_mcp_server(engine))


def _find_free_port(preferred: int, host: str) -> int:
    """Return ``preferred`` if free, otherwise the next available port.

    Scans up to 20 ports past ``preferred`` before giving up.

    Args:
        preferred: Port to try first.
        host: Interface to bind against while probing.

    Returns:
        A port number that is currently free on ``host``.

    Raises:
        OSError: If no free port is found within the scan window.
    """
    import socket  # noqa: PLC0415

    for candidate in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, candidate))
            except OSError:
                continue
            return candidate
    raise OSError(f"No free port in range [{preferred}, {preferred + 20})")


playground_app = typer.Typer(
    help="Bricks Playground \u2014 web UI and headless scenario runner.",
    invoke_without_command=True,
    no_args_is_help=False,
)
app.add_typer(playground_app, name="playground")


@playground_app.callback()
def _playground_root(
    ctx: typer.Context,
    port: int = typer.Option(8080, "--port", help="Port to bind. Probes for a free port starting here."),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind. Use 0.0.0.0 for LAN access."),
    no_browser: bool = typer.Option(False, "--no-browser", help="Skip auto-opening the browser."),
    force_port: bool = typer.Option(
        False, "--force-port", help="Fail if --port is taken instead of probing for a free one."
    ),
) -> None:
    """Start the Bricks Playground web UI when invoked without a subcommand.

    Serves the Playground at ``http://{host}:{port}`` and opens the default
    browser to it. Ctrl+C shuts down cleanly. Use the ``run`` subcommand for
    a headless one-shot scenario run.
    """
    if ctx.invoked_subcommand is not None:
        # A subcommand (e.g. ``run``) is taking over; don't spin up the server.
        return

    import threading  # noqa: PLC0415
    import webbrowser  # noqa: PLC0415

    try:
        import uvicorn  # noqa: PLC0415
        from bricks_ai.playground.web.app import app as web_app  # noqa: PLC0415
    except ImportError as exc:
        typer.echo("Error: Playground features require the 'playground' extra.", err=True)
        typer.echo('Install with: pip install "bricks-ai[playground]"', err=True)
        raise typer.Exit(code=1) from exc

    if force_port:
        bound_port = port
    else:
        try:
            bound_port = _find_free_port(port, host)
        except OSError as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(code=1) from exc

    url = f"http://{'localhost' if host == '127.0.0.1' else host}:{bound_port}"
    # Plain ASCII so the banner renders on every platform \u2014 Python's
    # default Windows console codepage (cp1252) can't encode the
    # check-mark / arrow glyphs we used to ship and would crash here
    # before uvicorn even started.
    typer.echo(f"OK  Bricks Playground running -> {url}")

    if not no_browser:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()
        typer.echo("  (browser opened \u00b7 Ctrl+C to stop)")
    else:
        typer.echo("  (Ctrl+C to stop)")

    try:
        uvicorn.run(web_app, host=host, port=bound_port, log_level="warning")
    except KeyboardInterrupt:
        typer.echo("\nShutting down.")


@playground_app.command("run")
def playground_run(
    target: str = typer.Argument(..., help="Preset stem (e.g. 'crm_pipeline') or path to a scenario YAML."),
    provider: str = typer.Option(
        "",
        "--provider",
        help="LLM provider: claude_code | anthropic | openai | ollama. "
        "Inferred from the scenario's model alias when empty.",
    ),
    model: str = typer.Option(
        "",
        "--model",
        help="Override the scenario's model (e.g. 'gpt-4o-mini'). Empty = use scenario.model.",
    ),
    api_key: str = typer.Option(
        "",
        "--api-key",
        help="BYOK key. Resolution: this flag → BRICKS_API_KEY env → "
        "ANTHROPIC_API_KEY / OPENAI_API_KEY env. Ignored for claude_code / ollama.",
    ),
    compare_raw: bool = typer.Option(
        False, "--compare-raw", help="Also run the raw-LLM engine for side-by-side comparison."
    ),
) -> None:
    """Run a playground scenario headlessly and print input data, blueprint, outputs.

    Resolves *target* to a YAML path (preset stem under
    ``bricks/playground/presets/`` or a literal file path), constructs an
    LLM provider via :mod:`bricks_ai.llm.factory` (same
    factory the web UI uses), runs BricksEngine, and — with
    ``--compare-raw`` — RawLLMEngine alongside it.
    """
    try:
        from bricks_ai.llm.factory import (  # noqa: PLC0415
            build_provider,
            infer_provider,
            resolve_api_key,
        )
        from bricks_ai.playground.engine import BricksEngine, RawLLMEngine  # noqa: PLC0415
        from bricks_ai.playground.scenario_loader import load_scenario, resolve_preset  # noqa: PLC0415
    except ImportError as exc:
        typer.echo("Error: Playground features require the 'playground' extra.", err=True)
        typer.echo('Install with: pip install "bricks-ai[playground,ai]"', err=True)
        raise typer.Exit(code=1) from exc

    try:
        path = resolve_preset(target)
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    scenario = load_scenario(path)
    raw_data = _resolve_scenario_raw_data(scenario, base_dir=path.parent)

    typer.echo(f"=== INPUT DATA ({scenario.name}) ===")
    typer.echo(_pretty_truncate(raw_data, max_chars=2000))
    typer.echo("")

    effective_model = model or scenario.model
    if not provider:
        try:
            provider = infer_provider(effective_model)
        except ValueError as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(code=1) from exc

    resolved_key = resolve_api_key(provider, explicit=api_key)
    try:
        llm_provider = build_provider(provider=provider, model=effective_model, api_key=resolved_key)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    bricks_engine = BricksEngine(provider=llm_provider)
    bricks_result = bricks_engine.solve(scenario.task_text, raw_data)

    typer.echo("=== COMPOSED BLUEPRINT (bricks) ===")
    typer.echo((bricks_result.dsl_code or bricks_result.raw_response or "(empty)").rstrip())
    typer.echo("")

    typer.echo("=== OUTPUTS (bricks) ===")
    if bricks_result.error:
        typer.echo(f"ERROR: {bricks_result.error}")
    else:
        typer.echo(_pretty_dict(bricks_result.outputs))
    typer.echo("")

    if compare_raw:
        raw_engine = RawLLMEngine(provider=llm_provider)
        raw_result = raw_engine.solve(scenario.task_text, raw_data)
        typer.echo("=== OUTPUTS (raw_llm) ===")
        if raw_result.error:
            typer.echo(f"ERROR: {raw_result.error}")
        else:
            typer.echo(_pretty_dict(raw_result.outputs))


def _resolve_scenario_raw_data(scenario: Any, *, base_dir: Path) -> str:
    """Resolve a ScenarioDefinition's data source to a JSON string for the engines."""
    import json  # noqa: PLC0415

    from bricks_ai.playground.dataset_loader import DatasetLoader  # noqa: PLC0415

    if scenario.data is not None:
        return json.dumps(scenario.data)
    if scenario.data_file is not None:
        ref = Path(scenario.data_file)
        if not ref.is_absolute():
            ref = base_dir / ref
        return ref.read_text(encoding="utf-8")
    if scenario.dataset_id is not None:
        ds = DatasetLoader().get_dataset(scenario.dataset_id)
        if ds is None:
            typer.echo(f"Error: dataset {scenario.dataset_id!r} not found", err=True)
            raise typer.Exit(code=1)
        return json.dumps(ds["data"])
    typer.echo("Error: scenario has no data source", err=True)
    raise typer.Exit(code=1)


def _pretty_dict(d: dict[str, Any]) -> str:
    """Render an output dict line-by-line for ADHD-friendly CLI output."""
    if not d:
        return "(empty)"
    width = max(len(str(k)) for k in d)
    return "\n".join(f"  {k:<{width}}  {v!r}" for k, v in d.items())


def _pretty_truncate(text: str, *, max_chars: int) -> str:
    """Truncate noisy raw data to ``max_chars`` with a marker."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... (truncated, {len(text) - max_chars} more chars)"
