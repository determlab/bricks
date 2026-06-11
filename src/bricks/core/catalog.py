"""TieredCatalog: smart three-tier brick discovery for AI agents."""

from __future__ import annotations

from typing import Any

from bricks.core.registry import BrickRegistry
from bricks.core.schema import brick_schema


class TieredCatalog:
    """Three-tier brick discovery designed for AI agent consumption.

    Tiers:
    - **Tier 1 (common set):** user-configured list of brick names always
      returned by :meth:`list_bricks`. Configured via ``catalog.common_set``
      in ``bricks.config.yaml``.
    - **Tier 2 (search):** :meth:`lookup_brick` searches name, tags, and
      description for a query substring. Matching bricks are added to the
      session cache (Tier 3).
    - **Tier 3 (session cache):** bricks recently accessed via
      :meth:`lookup_brick` or :meth:`get_brick` are remembered for the
      session and included in :meth:`list_bricks` results.

    This design lets AI agents start with a small, focused view of the
    registry and progressively discover more bricks without receiving an
    overwhelming full dump on every call.
    """

    def __init__(
        self,
        registry: BrickRegistry,
        common_set: list[str] | None = None,
    ) -> None:
        """Initialise the catalog.

        Args:
            registry: The brick registry to query.
            common_set: Names of bricks always shown in :meth:`list_bricks`.
                Unknown names are silently ignored.
        """
        self._registry = registry
        self._common_set: list[str] = common_set or []
        self._session_cache: list[str] = []

    # ── Public API ────────────────────────────────────────────────────────────

    def list_bricks(self) -> list[dict[str, Any]]:
        """Return Tier 1 (common set) + Tier 3 (session cache), deduplicated.

        Unknown names in the common set are silently skipped. The result
        preserves common-set order, with session-cache additions appended.

        Returns:
            List of brick schema dicts for each visible brick.
        """
        seen: set[str] = set()
        result: list[dict[str, Any]] = []

        for name in self._common_set:
            if name not in seen and self._registry.has(name):
                result.append(brick_schema(name, self._registry))
                seen.add(name)

        for name in self._session_cache:
            if name not in seen and self._registry.has(name):
                result.append(brick_schema(name, self._registry))
                seen.add(name)

        return result

    def lookup_brick(self, query: str) -> list[dict[str, Any]]:
        """Search bricks by name, tags, or description (Tier 2).

        Performs a case-insensitive substring match against each brick's
        name, tag list, and description. All matching bricks are added to
        the session cache (Tier 3).

        Args:
            query: Substring to search for.

        Returns:
            List of brick schema dicts for all matching bricks.
        """
        q = query.lower()
        results: list[dict[str, Any]] = []

        for name, meta in self._registry.list_all():
            match = q in name.lower() or q in meta.description.lower() or any(q in tag.lower() for tag in meta.tags)
            if match:
                results.append(brick_schema(name, self._registry))
                if name not in self._session_cache:
                    self._session_cache.append(name)

        return results

    def get_brick(self, name: str) -> dict[str, Any]:
        """Fetch a single brick by exact name and add it to the session cache.

        Args:
            name: Exact registered brick name.

        Returns:
            Brick schema dict.

        Raises:
            BrickNotFoundError: If the name is not registered.
        """
        schema = brick_schema(name, self._registry)  # raises BrickNotFoundError if missing
        if name not in self._session_cache:
            self._session_cache.append(name)
        return schema

    def clear_session_cache(self) -> None:
        """Reset the session cache (Tier 3)."""
        self._session_cache.clear()
