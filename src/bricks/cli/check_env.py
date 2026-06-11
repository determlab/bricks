"""CLI command: bricks check-env — diagnose the local environment."""

from __future__ import annotations

import sys

import typer


def check_env() -> None:
    """Diagnose the local environment for common Bricks setup issues.

    Checks Python version, platform, litellm availability, and (on Windows)
    the MAX_PATH limit that can break installation of packages with deeply
    nested file paths.
    """
    _print_section("System")
    typer.echo(f"  Platform : {sys.platform}")
    typer.echo(f"  Python   : {sys.version.split()[0]}")

    _check_python_version()

    _print_section("litellm")
    _check_litellm()

    if sys.platform == "win32":
        _print_section("Windows path limits")
        _check_windows_path()

    _print_section("Done")
    typer.echo("  Run 'bricks --help' to get started.")


# ── helpers ──────────────────────────────────────────────────────────────────


def _print_section(title: str) -> None:
    """Print a section header.

    Args:
        title: Section title string.
    """
    typer.echo(f"\n[{title}]")


def _check_python_version() -> None:
    """Warn if Python is below 3.10."""
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 10):
        typer.echo(f"  WARNING  Python {major}.{minor} < 3.10 — bricks-ai requires 3.10+", err=True)
    else:
        typer.echo(f"  OK       Python {major}.{minor} >= 3.10")


def _check_litellm() -> None:
    """Check whether litellm is importable and report its version."""
    try:
        import litellm  # noqa: PLC0415  # type: ignore[import-untyped]

        version = getattr(litellm, "__version__", "unknown")
        typer.echo(f"  OK       litellm {version}")
    except ImportError:
        typer.echo(
            '  WARNING  litellm not installed.\n           Install with: pip install "bricks-ai[ai]"',
            err=True,
        )


def _check_windows_path() -> None:
    """Check Windows MAX_PATH (260-char) limit and long-path registry setting."""
    typer.echo("  INFO     Windows MAX_PATH default = 260 characters.")
    typer.echo("           litellm installs files that exceed this limit.")

    long_paths_enabled = _read_long_paths_registry()
    if long_paths_enabled is True:
        typer.echo("  OK       LongPathsEnabled = 1 (registry)")
    elif long_paths_enabled is False:
        typer.echo(
            "  WARNING  LongPathsEnabled = 0 — pip install may fail with path errors.\n"
            "           Fix: enable long paths via Group Policy or registry:\n"
            "             HKLM\\SYSTEM\\CurrentControlSet\\Control\\FileSystem\n"
            "             LongPathsEnabled = 1\n"
            "           Or install bricks-ai in a shallow directory (e.g. C:\\bricks\\).",
            err=True,
        )
    else:
        typer.echo(
            "  WARNING  Could not read LongPathsEnabled registry key.\n"
            "           If pip install fails with path errors, see README Windows Setup section.",
            err=True,
        )


def _read_long_paths_registry() -> bool | None:
    """Read the Windows LongPathsEnabled registry value.

    Returns:
        True if enabled, False if disabled, None if unreadable.
    """
    try:
        import winreg  # noqa: PLC0415  # type: ignore[import]

        key = winreg.OpenKey(  # type: ignore[attr-defined]
            winreg.HKEY_LOCAL_MACHINE,  # type: ignore[attr-defined]
            r"SYSTEM\CurrentControlSet\Control\FileSystem",
        )
        value, _ = winreg.QueryValueEx(key, "LongPathsEnabled")  # type: ignore[attr-defined]
        winreg.CloseKey(key)  # type: ignore[attr-defined]
        return bool(value)
    except OSError:
        return None
