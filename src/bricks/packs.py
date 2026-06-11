"""Pack discovery — scans ``bricks.packs`` entry points at runtime."""

from __future__ import annotations

import importlib
import importlib.metadata

from bricks.core.registry import BrickRegistry
from bricks.errors import BricksConfigError


def discover_and_load(registry: BrickRegistry) -> int:
    """Discover installed brick packs and load them into *registry*.

    Iterates the ``bricks.packs`` entry point group, imports each pack's
    module, and calls its ``register(registry)`` function.

    Args:
        registry: The registry to populate with discovered bricks.

    Returns:
        Number of packs loaded.

    Raises:
        BricksConfigError: If no packs are installed.
    """
    eps = list(importlib.metadata.entry_points(group="bricks.packs"))
    if not eps:
        raise BricksConfigError("No brick packs installed. Run: pip install bricks-stdlib")
    for ep in eps:
        module = importlib.import_module(ep.value)
        module.register(registry)
    return len(eps)
