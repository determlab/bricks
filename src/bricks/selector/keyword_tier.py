"""Tier 1: keyword, tag, category, and type matching.

Deterministic and zero-cost. Scores each brick by counting how many
query fields it satisfies. Any brick with a score > 0 is a candidate.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any, get_args, get_origin

from bricks.core.models import BrickMeta
from bricks.selector.base import BrickQuery, SelectionTier


def _type_names(callable_: Callable[..., Any]) -> tuple[list[str], list[str]]:
    """Extract input and output type name strings from a callable's signature.

    Args:
        callable_: The brick callable to inspect.

    Returns:
        A tuple of ``(input_type_names, output_type_names)`` as lowercase strings.
    """
    try:
        sig = inspect.signature(callable_)
    except (ValueError, TypeError):
        return [], []

    input_names: list[str] = []
    for param in sig.parameters.values():
        if param.annotation is inspect.Parameter.empty:
            continue
        input_names.extend(_flatten_annotation(param.annotation))

    output_names: list[str] = []
    if sig.return_annotation is not inspect.Parameter.empty:
        output_names.extend(_flatten_annotation(sig.return_annotation))

    return input_names, output_names


def _flatten_annotation(annotation: Any) -> list[str]:
    """Recursively extract simple type name strings from a type annotation.

    Handles ``Union[X, Y]``, ``Optional[X]``, ``list[X]``, etc.

    Args:
        annotation: A type annotation object.

    Returns:
        List of lowercase type name strings found inside the annotation.
    """
    origin = get_origin(annotation)
    if origin is not None:
        # Generic alias (Union, list, dict, …) — recurse into args
        names = []
        for arg in get_args(annotation):
            names.extend(_flatten_annotation(arg))
        return names
    name = getattr(annotation, "__name__", None) or str(annotation)
    return [name.lower()]


class KeywordTier(SelectionTier):
    """Tier 1 keyword selector — deterministic, zero LLM cost.

    Scores bricks by summing:

    - ``+1`` for each query category matching ``meta.category``
    - ``+1`` for each query tag found in ``meta.tags``
    - ``+1`` for each query keyword found (case-insensitive) in the brick's
      combined ``name + description`` text
    - ``+1`` for each query input type matching a brick parameter type
    - ``+1`` for each query output type matching the brick's return type

    Any score > 0 is a candidate.
    """

    def score(
        self,
        query: BrickQuery,
        name: str,
        meta: BrickMeta,
        callable_: Callable[..., Any],
    ) -> float:
        """Score this brick against the query.

        Args:
            query: The structured selection query.
            name: Registered brick name.
            meta: Brick metadata.
            callable_: The registered callable for the brick.

        Returns:
            A non-negative float score. Zero means no match.
        """
        score = 0.0

        if query.categories:
            score += sum(1 for cat in query.categories if cat.lower() == meta.category.lower())

        if query.tags:
            meta_tags_lower = {t.lower() for t in meta.tags}
            score += sum(1 for tag in query.tags if tag.lower() in meta_tags_lower)

        if query.keywords:
            haystack = (name + " " + meta.description).lower()
            score += sum(1 for kw in query.keywords if kw.lower() in haystack)

        if query.input_types or query.output_types:
            in_types, out_types = _type_names(callable_)
            if query.input_types:
                score += sum(1 for t in query.input_types if t.lower() in in_types)
            if query.output_types:
                score += sum(1 for t in query.output_types if t.lower() in out_types)

        return score
