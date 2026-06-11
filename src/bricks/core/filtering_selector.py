"""FilteringSelector — wraps another selector and excludes named bricks.

Used by the tier-40 :class:`~bricks_ai.healing.FullRecomposeHealer` when
prior healing attempts identified specific bricks that the LLM keeps
misusing. By dropping those bricks from the pool before the next compose,
the LLM is forced to pick an alternative.
"""

from __future__ import annotations

from collections.abc import Iterable

from bricks.core.registry import BrickRegistry
from bricks.core.selector import BrickSelector


class FilteringSelector(BrickSelector):
    """Wrap another :class:`BrickSelector` and drop named bricks from its result.

    The inner selector runs first; this one rebuilds its registry without
    the excluded names. Registrations are copied via the public registry
    API (``register``) rather than mutating private state.

    Args:
        inner: The selector whose pool we post-filter.
        exclude: Brick names to drop. Missing names are silently ignored —
            the filter is a superset, not an invariant.
    """

    def __init__(self, inner: BrickSelector, exclude: Iterable[str]) -> None:
        """Initialise with an inner selector and a set of names to exclude."""
        self._inner = inner
        self._exclude = set(exclude)

    @property
    def excluded(self) -> frozenset[str]:
        """Read-only view of the exclusion set — for tests and logs."""
        return frozenset(self._exclude)

    def select(self, task: str, registry: BrickRegistry) -> BrickRegistry:
        """Return a registry containing the inner pool minus excluded names.

        Args:
            task: Natural language task (passed to the inner selector).
            registry: Full registry to select from.

        Returns:
            A fresh :class:`BrickRegistry` that omits every excluded name.
            If nothing is excluded, returns the inner result unchanged.
        """
        pool = self._inner.select(task, registry)
        if not self._exclude:
            return pool

        filtered = BrickRegistry()
        for name, meta in pool.list_all():
            if name in self._exclude:
                continue
            callable_, _ = pool.get(name)
            filtered.register(name, callable_, meta)
        return filtered
