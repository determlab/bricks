"""Tier 2: embedding cosine-similarity selector.

Near-zero cost. Compares the task embedding against each brick's
description embedding. Requires a configured ``EmbeddingProvider``.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from bricks.core.models import BrickMeta
from bricks.selector.base import BrickQuery, SelectionTier


class EmbeddingProvider(ABC):
    """ABC for embedding backends used by ``EmbeddingTier``.

    Implement this interface to plug in any embedding service
    (OpenAI, local sentence-transformers, etc.).
    """

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return embeddings for a list of texts.

        Args:
            texts: Input strings to embed.

        Returns:
            A list of float vectors, one per input text.
            Implementations should return unit-normalised vectors to make
            cosine similarity equivalent to dot product.
        """
        ...


def _cosine(a: list[float], b: list[float]) -> float:
    """Return cosine similarity between two vectors.

    Args:
        a: First vector.
        b: Second vector (must be same length as *a*).

    Returns:
        Cosine similarity in [-1, 1]. Returns 0.0 for zero-length vectors.
    """
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


class EmbeddingTier(SelectionTier):
    """Tier 2 selector using embedding cosine similarity.

    Compares the query task text embedding against each brick's
    ``name + description`` embedding. Returns the cosine similarity as
    the score so that the top-k most similar bricks are selected.

    The ``query_text`` attribute must be set to the original task string
    before ``score()`` is called. ``TieredBrickSelector`` does this
    automatically by setting ``tier._query_text = task``.

    Args:
        provider: The embedding backend to use.
        query_text: Initial query text (typically overridden per-call).
    """

    def __init__(
        self,
        provider: EmbeddingProvider,
        query_text: str = "",
    ) -> None:
        """Initialise the embedding tier.

        Args:
            provider: Embedding backend.
            query_text: Task text to embed as the query vector.
        """
        self._provider = provider
        self._query_text = query_text
        self._query_vec: list[float] | None = None
        self._brick_vecs: dict[str, list[float]] = {}

    def _get_query_vec(self) -> list[float]:
        """Return the cached query embedding, computing it if needed.

        Returns:
            Query embedding vector.
        """
        if self._query_vec is None:
            vecs = self._provider.embed([self._query_text])
            self._query_vec = vecs[0] if vecs else []
        return self._query_vec

    def _get_brick_vec(self, name: str, meta: BrickMeta) -> list[float]:
        """Return the cached brick embedding for ``name``.

        Args:
            name: Brick name (cache key).
            meta: Brick metadata (used to build text if not cached).

        Returns:
            Brick embedding vector.
        """
        if name not in self._brick_vecs:
            text = name + " " + meta.description
            vecs = self._provider.embed([text])
            self._brick_vecs[name] = vecs[0] if vecs else []
        return self._brick_vecs[name]

    def invalidate_cache(self) -> None:
        """Clear the query and brick embedding caches.

        Call when ``query_text`` changes between ``score()`` calls.
        """
        self._query_vec = None
        self._brick_vecs.clear()

    def score(
        self,
        query: BrickQuery,
        name: str,
        meta: BrickMeta,
        callable_: Callable[..., Any],
    ) -> float:
        """Return cosine similarity between the task and this brick.

        Args:
            query: Structured selection query (not used directly; embedding
                   uses ``self._query_text``).
            name: Registered brick name.
            meta: Brick metadata.
            callable_: The registered callable (unused).

        Returns:
            Cosine similarity in [0, 1]. Returns 0.0 if provider returns
            empty vectors or if ``query_text`` is empty.
        """
        if not self._query_text:
            return 0.0
        qvec = self._get_query_vec()
        bvec = self._get_brick_vec(name, meta)
        if not qvec or not bvec:
            return 0.0
        return max(0.0, _cosine(qvec, bvec))
