"""Typer CLI application with all Bricks commands."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import typer

from bricks.cli.check_env import check_env as _check_env_fn
from bricks.core.config import BricksConfig, ConfigLoader
from bricks.core.discovery import BrickDiscovery
from bricks.core.engine import BlueprintEngine
from bricks.core.exceptions import (
    BlueprintValidationError,
    BrickExecutionError,
    YamlLoadError,
)
from bricks.core.loader import BlueprintLoader
from bricks.core.models import Verbosity
from bricks.core.registry import BrickRegistry
from bricks.core.validation import BlueprintValidator

app = typer.Typer(
    name="bricks",
    help="Bricks - Deterministic sequencing engine for typed Python building blocks.",
    no_args_is_help=True,
)

new_app = typer.Typer(help="Scaffold new Bricks components.")
app.add_typer(new_app, name="new")


def _setup_registry(
    config_dir: Path | None = None,
) -> tuple[BrickRegistry, BricksConfig]:
    """Load config and set up registry with auto-discovery.

    Args:
        config_dir: Directory to search for bricks.config.yaml. Defaults to cwd.

    Returns:
        A tuple of (registry, config).
    """
    loader = ConfigLoader()
    config = loader.load(directory=config_dir)
    registry = BrickRegistry()
    if config.registry.auto_discover:
        discovery = BrickDiscovery(registry=registry)
        for path_str in config.registry.paths:
            p = Path(path_str)
            if not p.is_absolute():
                p = (config_dir or Path.cwd()) / p
            if p.is_dir():
                discovery.discover_package(p)
            elif p.suffix == ".py" and p.exists():
                discovery.discover_path(p)
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
    """Scaffold a new Brick module."""
    snake_name = name.lower().replace("-", "_").replace(" ", "_")
    class_name = "".join(word.capitalize() for word in snake_name.split("_"))

    output_path = Path.cwd() / "bricks_lib" / f"{snake_name}.py"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    content = f'''"""Brick: {snake_name}."""

from __future__ import annotations

from bricks.core import BrickMeta, BrickModel, BaseBrick


class {class_name}(BaseBrick):
    """{class_name} brick."""

    class Meta:
        """Brick metadata."""

        name = "{snake_name}"
        tags: list[str] = []
        destructive: bool = False
        idempotent: bool = True
        description = ""

    class Input(BrickModel):
        """Input schema."""

    class Output(BrickModel):
        """Output schema."""

    def execute(self, inputs: BrickModel, metadata: BrickMeta) -> dict[str, object]:
        """Execute the brick.

        Args:
            inputs: Validated input data.
            metadata: Brick metadata.

        Returns:
            Output dict matching Output schema.
        """
        raise NotImplementedError(f"{{{class_name}}} is not yet implemented")
'''
    output_path.write_text(content)
    typer.echo(f"Created {output_path}")


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
def check(file: str = typer.Argument(..., help="Path to blueprint YAML file.")) -> None:
    """Validate a blueprint YAML file (lint without executing)."""
    path = Path(file)
    if not path.exists():
        typer.echo(f"Error: File not found: {path}", err=True)
        raise typer.Exit(code=1)

    bp_loader = BlueprintLoader()
    try:
        blueprint = bp_loader.load_file(path)
    except YamlLoadError as exc:
        typer.echo(f"Error loading YAML: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    registry, _ = _setup_registry()
    validator = BlueprintValidator(registry=registry)

    try:
        validator.validate(blueprint)
        typer.echo(f"valid: {path}")
    except BlueprintValidationError as exc:
        typer.echo(f"Validation errors in {path}:", err=True)
        if exc.errors:
            for error in exc.errors:
                typer.echo(f"  - {error}", err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def run(
    sequence: str = typer.Argument(..., help="Path to blueprint YAML file."),
    input_: list[str] = typer.Option(  # noqa: B008
        [], "--input", "-i", help="Input values as key=value."
    ),
    verbosity: Verbosity = typer.Option(  # noqa: B008
        Verbosity.MINIMAL, "--verbosity", "-v", help="Output detail level (minimal/standard/full)."
    ),
) -> None:
    """Execute a blueprint."""
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

    inputs: dict[str, object] = {}
    for item in input_:
        if "=" not in item:
            typer.echo(f"Error: Invalid input format {item!r}. Use key=value.", err=True)
            raise typer.Exit(code=1)
        k, v = item.split("=", 1)
        try:
            inputs[k] = json.loads(v)
        except json.JSONDecodeError:
            inputs[k] = v

    registry, _ = _setup_registry()
    engine = BlueprintEngine(registry=registry)

    try:
        exec_result = engine.run(bp_def, inputs=inputs or None, verbosity=verbosity)
    except BrickExecutionError as exc:
        typer.echo(f"Execution error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

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
def list_bricks() -> None:
    """List all available Bricks in the registry."""
    registry, _ = _setup_registry()
    all_bricks = registry.list_all()

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
