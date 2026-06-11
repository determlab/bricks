"""Base types for the tiered brick selection system.

Provides:
- ``BrickQuery`` — structured query model consumed by selection tiers.
- ``SelectionTier`` — ABC for individual scoring tiers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from bricks.core.models import BrickMeta


class BrickQuery(BaseModel):
    """Structured query for brick selection.

    Each non-empty field narrows the search. A tier scores a brick higher
    the more query fields it satisfies.

    Attributes:
        categories: Brick categories to match against ``BrickMeta.category``.
        input_types: Expected input type names (matched against parameter annotations).
        output_types: Expected output type names (matched against return annotation).
        tags: Tags to match against ``BrickMeta.tags``.
        keywords: Free-text keywords matched against brick name and description.
    """

    categories: list[str] = Field(default_factory=list)
    input_types: list[str] = Field(default_factory=list)
    output_types: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class SelectionTier(ABC):
    """ABC for a single scoring tier used by ``TieredBrickSelector``.

    Each tier receives a ``BrickQuery`` and a single brick's metadata and
    callable, and returns a non-negative relevance score. A score of 0.0
    means the tier does not consider the brick relevant.
    """

    @abstractmethod
    def score(
        self,
        query: BrickQuery,
        name: str,
        meta: BrickMeta,
        callable_: Callable[..., Any],
    ) -> float:
        """Return a relevance score >= 0.0 for this brick.

        Args:
            query: The structured selection query.
            name: Registered brick name.
            meta: Brick metadata.
            callable_: The registered callable for the brick.

        Returns:
            A non-negative float. Zero means no match.
        """
        ...
