"""BrickRegistry: stores and retrieves registered Bricks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from bricks.core.exceptions import BrickNotFoundError, DuplicateBrickError
from bricks.core.models import BrickMeta


class BrickRegistry:
    """Global registry that stores Bricks (functions or class instances) by name.

    Each registered name must be unique. Attempting to register a duplicate
    raises ``DuplicateBrickError``.
    """

    def __init__(self) -> None:
        self._bricks: dict[str, tuple[Callable[..., Any], BrickMeta]] = {}

    def register(self, name: str, callable_: Callable[..., Any], meta: BrickMeta) -> None:
        """Register a brick by name.

        Args:
            name: Unique identifier for the brick.
            callable_: The function or class instance to register.
            meta: Brick metadata.

        Raises:
            DuplicateBrickError: If *name* is already registered.
        """
        if name in self._bricks:
            raise DuplicateBrickError(name)
        self._bricks[name] = (callable_, meta)

    def get(self, name: str) -> tuple[Callable[..., Any], BrickMeta]:
        """Retrieve a registered brick and its metadata.

        Args:
            name: The brick name to look up.

        Returns:
            A tuple of ``(callable, BrickMeta)``.

        Raises:
            BrickNotFoundError: If *name* is not registered.
        """
        if name not in self._bricks:
            raise BrickNotFoundError(name)
        return self._bricks[name]

    def list_all(self) -> list[tuple[str, BrickMeta]]:
        """Return all registered brick names and their metadata.

        Returns:
            List of ``(name, BrickMeta)`` tuples, sorted by name.
        """
        return [(name, meta) for name, (_, meta) in sorted(self._bricks.items())]

    def list_public(self) -> list[tuple[str, BrickMeta]]:
        """Return public (non-built-in) brick names and their metadata.

        Excludes any brick whose name starts with ``__`` (built-in bricks).

        Returns:
            List of ``(name, BrickMeta)`` tuples, sorted by name.
        """
        return [(name, meta) for name, meta in self.list_all() if not name.startswith("__")]

    def has(self, name: str) -> bool:
        """Check if a brick name is registered.

        Args:
            name: The brick name to check.

        Returns:
            True if registered, False otherwise.
        """
        return name in self._bricks

    def clear(self) -> None:
        """Remove all registered bricks. Primarily for testing."""
        self._bricks.clear()

    @classmethod
    def from_stdlib(cls) -> BrickRegistry:
        """Create a registry pre-populated with all installed stdlib bricks.

        Calls ``bricks.packs.discover_and_load`` to register every brick
        from all installed ``bricks.packs`` entry points.

        Returns:
            A new :class:`BrickRegistry` with all stdlib bricks registered.

        Raises:
            BricksConfigError: If no brick packs are installed.
        """
        from bricks.packs import discover_and_load  # noqa: PLC0415 — avoid circular at module level

        registry = cls()
        discover_and_load(registry)
        return registry
