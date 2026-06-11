"""TieredBrickSelector: multi-tier registry filtering with safe fallback.

Tier 1 (keyword) runs first. Tier 2 (embedding) only runs when Tier 1
returns 0 results. If all tiers return 0 results, the full registry is
returned unchanged.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from bricks.core.models import BrickMeta
from bricks.core.registry import BrickRegistry
from bricks.core.selector import BrickSelector
from bricks.selector.base import BrickQuery, SelectionTier
from bricks.selector.embedding_tier import EmbeddingTier

_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "to",
        "of",
        "for",
        "and",
        "or",
        "with",
        "in",
        "on",
        "at",
        "by",
        "is",
        "are",
        "was",
        "be",
        "as",
        "it",
    }
)


def _build_query(task: str) -> BrickQuery:
    """Tokenise a task string into a keyword-only ``BrickQuery``.

    Splits on word characters, lowercases, removes stopwords and
    single/two-character tokens.

    Args:
        task: Natural language task description.

    Returns:
        A ``BrickQuery`` with ``keywords`` populated and all other
        fields empty.
    """
    words = re.findall(r"[a-z]+", task.lower())
    keywords = [w for w in words if w not in _STOPWORDS and len(w) > 2]
    return BrickQuery(keywords=keywords)


def _build_sub_registry(
    names_scores: list[tuple[str, float]],
    source: BrickRegistry,
) -> BrickRegistry:
    """Build a new ``BrickRegistry`` from a scored brick list.

    Args:
        names_scores: List of ``(name, score)`` tuples. Order need not
                      be sorted; they are registered in the given order.
        source: Registry to copy bricks from.

    Returns:
        A new ``BrickRegistry`` containing only the named bricks.
    """
    sub = BrickRegistry()
    for name, _ in names_scores:
        callable_: Callable[..., Any]
        meta: BrickMeta
        callable_, meta = source.get(name)
        sub.register(name, callable_, meta)
    return sub


class TieredBrickSelector(BrickSelector):
    """Multi-tier brick selector with deterministic fallback.

    Runs selection tiers in order. The first tier that returns at least
    one match wins — subsequent tiers are not consulted. If no tier
    produces results, the full source registry is returned unchanged so
    that composition never silently loses bricks.

    Args:
        tiers: Ordered list of ``SelectionTier`` instances.
        max_results: Maximum number of bricks to return. Tier output is
                     sorted by descending score and trimmed to this limit.
    """

    def __init__(
        self,
        tiers: list[SelectionTier],
        max_results: int = 20,
    ) -> None:
        """Initialise the tiered selector.

        Args:
            tiers: Scoring tiers to run in order.
            max_results: Upper limit on returned bricks.
        """
        self._tiers = tiers
        self._max_results = max_results

    def select(self, task: str, registry: BrickRegistry) -> BrickRegistry:
        """Select bricks relevant to *task* from *registry*.

        Tokenises *task* into a ``BrickQuery`` then delegates to
        :meth:`select_query`.

        Args:
            task: Natural language task description.
            registry: Full brick registry to filter.

        Returns:
            A filtered ``BrickRegistry`` (at most ``max_results`` bricks),
            or the original registry if all tiers matched nothing.
        """
        query = _build_query(task)
        return self.select_query(query, registry, task=task)

    def select_query(
        self,
        query: BrickQuery,
        registry: BrickRegistry,
        *,
        task: str = "",
    ) -> BrickRegistry:
        """Select bricks using a pre-built ``BrickQuery``.

        Allows callers to pass a structured query directly (e.g. when the
        query was built externally or populated with explicit types/tags).

        Args:
            query: Structured brick selection query.
            registry: Full brick registry to filter.
            task: Original task text. Required for ``EmbeddingTier`` to
                  build the query vector; safe to omit for keyword-only use.

        Returns:
            A filtered ``BrickRegistry`` (at most ``max_results`` bricks),
            or the original registry if all tiers matched nothing.
        """
        all_bricks = registry.list_all()

        for tier in self._tiers:
            if isinstance(tier, EmbeddingTier) and task and tier._query_text != task:
                tier._query_text = task
                tier.invalidate_cache()

            scored = [
                (name, s)
                for name, meta in all_bricks
                if (s := tier.score(query, name, meta, registry.get(name)[0])) > 0
            ]

            if scored:
                top = sorted(scored, key=lambda x: x[1], reverse=True)[: self._max_results]
                return _build_sub_registry(top, registry)

        # All tiers returned 0 results — safe fallback to full registry.
        return registry
