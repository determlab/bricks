"""bricks-stdlib — Standard library of reusable bricks for the Bricks engine.

95 bricks across 7 categories, auto-registered via the ``bricks.packs`` entry
point when ``bricks-stdlib`` is installed alongside ``bricks``.

Usage (direct)::

    from bricks.stdlib import register
    from bricks.core.registry import BrickRegistry

    registry = BrickRegistry()
    register(registry)
"""

from __future__ import annotations

from bricks.core.registry import BrickRegistry
from bricks.stdlib import (
    data_transformation,
    date_time,
    encoding_security,
    list_operations,
    math_numeric,
    string_processing,
    validation,
)

__all__ = ["register"]


def register(registry: BrickRegistry) -> None:
    """Register all stdlib bricks into the provided registry.

    Called automatically by the Bricks entry point discovery system.
    Can also be called directly when you need fine-grained control over
    which registry receives the stdlib bricks.

    Args:
        registry: The :class:`~bricks.core.registry.BrickRegistry` to
            populate with all 95 stdlib bricks across 7 categories:
            data_transformation (25), string_processing (20),
            math_numeric (10), date_time (10), validation (10),
            list_operations (10), encoding_security (10).
    """
    modules = [
        data_transformation,
        string_processing,
        math_numeric,
        date_time,
        validation,
        list_operations,
        encoding_security,
    ]

    for module in modules:
        for name in dir(module):
            obj = getattr(module, name)
            if callable(obj) and hasattr(obj, "__brick_meta__"):
                registry.register(name, obj, obj.__brick_meta__)
