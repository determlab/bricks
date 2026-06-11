"""Tests for bricks.selector — tiered brick selection."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from bricks.core.models import BrickMeta
from bricks.core.registry import BrickRegistry
from bricks.selector.base import BrickQuery, SelectionTier
from bricks.selector.embedding_tier import EmbeddingProvider, EmbeddingTier
from bricks.selector.keyword_tier import KeywordTier
from bricks.selector.selector import TieredBrickSelector, _build_query

# ── Helpers ────────────────────────────────────────────────────────────────


def _meta(
    name: str,
    *,
    category: str = "general",
    tags: list[str] | None = None,
    description: str = "",
) -> BrickMeta:
    """Build a BrickMeta for testing."""
    return BrickMeta(
        name=name,
        category=category,
        tags=tags or [],
        description=description,
    )


def _reg(*entries: tuple[str, BrickMeta]) -> BrickRegistry:
    """Build a BrickRegistry from (name, meta) pairs."""
    reg = BrickRegistry()
    for name, meta in entries:
        reg.register(name, lambda: None, meta)
    return reg


def _big_registry(n: int = 50) -> BrickRegistry:
    """Build a registry with *n* bricks (mostly irrelevant to math)."""
    reg = BrickRegistry()
    for i in range(n):
        category = "math" if i < 5 else "general"
        description = "calculate quantity" if i < 5 else f"process record {i}"
        meta = BrickMeta(name=f"brick_{i:03d}", category=category, description=description)
        reg.register(f"brick_{i:03d}", lambda: None, meta)
    return reg


# ── TestBrickQuery ──────────────────────────────────────────────────────────


class TestBrickQuery:
    """Tests for the BrickQuery model."""

    def test_defaults_are_empty_lists(self) -> None:
        """All BrickQuery fields default to empty lists."""
        q = BrickQuery()
        assert q.categories == []
        assert q.input_types == []
        assert q.output_types == []
        assert q.tags == []
        assert q.keywords == []

    def test_field_population(self) -> None:
        """BrickQuery fields accept values correctly."""
        q = BrickQuery(categories=["math"], tags=["fast"], keywords=["round"])
        assert q.categories == ["math"]
        assert q.tags == ["fast"]
        assert q.keywords == ["round"]


# ── TestBuildQuery ──────────────────────────────────────────────────────────


class TestBuildQuery:
    """Tests for _build_query() tokenisation."""

    def test_stopwords_removed(self) -> None:
        """Common stopwords are excluded from keywords."""
        q = _build_query("calculate the sum of values")
        assert "the" not in q.keywords
        assert "of" not in q.keywords

    def test_short_words_excluded(self) -> None:
        """Tokens with <= 2 characters are excluded."""
        q = _build_query("sum up all")
        assert "up" not in q.keywords
        # "all" is 3 chars and not a stopword — should be included
        assert "all" in q.keywords

    def test_lowercase_normalisation(self) -> None:
        """Tokens are lowercased."""
        q = _build_query("Calculate PROPERTY Valuation")
        assert all(kw == kw.lower() for kw in q.keywords)

    def test_produces_keywords(self) -> None:
        """Task with meaningful words produces non-empty keywords."""
        q = _build_query("calculate property valuation using price")
        assert len(q.keywords) > 0

    def test_empty_task(self) -> None:
        """Empty task produces empty keywords."""
        q = _build_query("")
        assert q.keywords == []


# ── TestKeywordTier ─────────────────────────────────────────────────────────


class TestKeywordTier:
    """Tests for KeywordTier scoring."""

    def _score(
        self,
        query: BrickQuery,
        name: str = "test_brick",
        category: str = "general",
        tags: list[str] | None = None,
        description: str = "",
    ) -> float:
        tier = KeywordTier()
        meta = _meta(name, category=category, tags=tags or [], description=description)
        return tier.score(query, name, meta, lambda: None)

    def test_keyword_match_in_name(self) -> None:
        """Keyword found in brick name scores > 0."""
        q = BrickQuery(keywords=["calculate"])
        score = self._score(q, name="calculate_sum")
        assert score > 0

    def test_keyword_match_in_description(self) -> None:
        """Keyword found in brick description scores > 0."""
        q = BrickQuery(keywords=["valuation"])
        score = self._score(q, description="computes property valuation")
        assert score > 0

    def test_keyword_no_match_returns_zero(self) -> None:
        """Keyword not in name/description returns 0."""
        q = BrickQuery(keywords=["zebra"])
        score = self._score(q, name="sum_values", description="add numbers together")
        assert score == 0.0

    def test_tag_match(self) -> None:
        """Query tag found in meta.tags scores +1."""
        q = BrickQuery(tags=["math"])
        score = self._score(q, tags=["math", "fast"])
        assert score >= 1.0

    def test_tag_no_match(self) -> None:
        """Query tag not in meta.tags scores 0 for that field."""
        q = BrickQuery(tags=["crypto"])
        score = self._score(q, tags=["math"])
        assert score == 0.0

    def test_category_match(self) -> None:
        """Query category matching meta.category scores +1."""
        q = BrickQuery(categories=["math"])
        score = self._score(q, category="math")
        assert score >= 1.0

    def test_category_no_match(self) -> None:
        """Query category not matching meta.category scores 0."""
        q = BrickQuery(categories=["math"])
        score = self._score(q, category="string")
        assert score == 0.0

    def test_score_is_additive(self) -> None:
        """Multiple matching fields produce a higher score than one."""
        q_multi = BrickQuery(keywords=["calc"], tags=["math"])
        q_single = BrickQuery(keywords=["calc"])
        s_multi = self._score(q_multi, name="calc_value", tags=["math"])
        s_single = self._score(q_single, name="calc_value")
        assert s_multi > s_single

    def test_empty_query_scores_zero(self) -> None:
        """An empty query scores 0 for every brick."""
        q = BrickQuery()
        score = self._score(q, name="sum_values", description="add numbers")
        assert score == 0.0

    def test_case_insensitive_keyword(self) -> None:
        """Keyword matching is case-insensitive."""
        q = BrickQuery(keywords=["CALC"])
        score = self._score(q, description="calc_value computes something")
        assert score > 0


# ── TestTieredBrickSelector ─────────────────────────────────────────────────


class TestTieredBrickSelector:
    """Tests for TieredBrickSelector."""

    def test_keyword_selects_relevant_subset(self) -> None:
        """Selector returns only math bricks when task mentions 'calculate'."""
        reg = _big_registry(50)  # first 5 bricks have category=math, description='calculate quantity'
        selector = TieredBrickSelector(tiers=[KeywordTier()], max_results=20)
        result = selector.select("calculate quantity", reg)
        names = [name for name, _ in result.list_all()]
        # All returned bricks should be from the math group (brick_000 to brick_004)
        assert all(name.startswith("brick_00") and int(name[-1]) < 5 for name in names), f"Unexpected: {names}"
        assert len(names) <= 20

    def test_max_results_respected(self) -> None:
        """max_results limits the number of returned bricks."""
        reg = BrickRegistry()
        for i in range(20):
            meta = BrickMeta(name=f"calc_{i}", description="calculate value")
            reg.register(f"calc_{i}", lambda: None, meta)
        selector = TieredBrickSelector(tiers=[KeywordTier()], max_results=5)
        result = selector.select("calculate value", reg)
        assert len(result.list_all()) <= 5

    def test_no_match_falls_back_to_full_registry(self) -> None:
        """When no tier matches, the full registry is returned unchanged."""
        reg = _reg(
            ("brick_a", _meta("brick_a", description="foo bar")),
            ("brick_b", _meta("brick_b", description="baz qux")),
        )
        selector = TieredBrickSelector(tiers=[KeywordTier()], max_results=20)
        # Use a query that won't match anything
        result = selector.select_query(BrickQuery(keywords=["xyzzy_nonexistent"]), reg)
        assert len(result.list_all()) == len(reg.list_all())

    def test_tier1_hit_tier2_not_called(self) -> None:
        """When Tier 1 matches, Tier 2 is not consulted."""
        call_count: list[int] = [0]

        class CountingTier(SelectionTier):
            def score(
                self,
                query: BrickQuery,
                name: str,
                meta: BrickMeta,
                callable_: Callable[..., Any],
            ) -> float:
                call_count[0] += 1
                return 0.0

        reg = _reg(("calc_val", _meta("calc_val", description="calculate value")))
        selector = TieredBrickSelector(tiers=[KeywordTier(), CountingTier()], max_results=20)
        selector.select("calculate value", reg)
        assert call_count[0] == 0, "Tier 2 should not have been called"

    def test_tier1_miss_tier2_runs(self) -> None:
        """When Tier 1 returns 0, Tier 2 is tried."""
        call_count: list[int] = [0]

        class AlwaysMissTier(SelectionTier):
            def score(
                self,
                query: BrickQuery,
                name: str,
                meta: BrickMeta,
                callable_: Callable[..., Any],
            ) -> float:
                return 0.0

        class CountingTier(SelectionTier):
            def score(
                self,
                query: BrickQuery,
                name: str,
                meta: BrickMeta,
                callable_: Callable[..., Any],
            ) -> float:
                call_count[0] += 1
                return 1.0

        reg = _reg(("brick_a", _meta("brick_a")))
        selector = TieredBrickSelector(tiers=[AlwaysMissTier(), CountingTier()], max_results=20)
        selector.select_query(BrickQuery(keywords=["anything"]), reg)
        assert call_count[0] > 0, "Tier 2 should have been called"

    def test_select_query_direct(self) -> None:
        """select_query() with an explicit BrickQuery works correctly."""
        reg = _reg(
            ("math_add", _meta("math_add", category="math", description="add numbers")),
            ("str_upper", _meta("str_upper", category="string", description="uppercase text")),
        )
        selector = TieredBrickSelector(tiers=[KeywordTier()], max_results=20)
        result = selector.select_query(BrickQuery(categories=["math"]), reg)
        names = [name for name, _ in result.list_all()]
        assert "math_add" in names
        assert "str_upper" not in names

    def test_no_tiers_falls_back_to_full_registry(self) -> None:
        """Zero tiers configured returns full registry safely."""
        reg = _reg(
            ("a", _meta("a")),
            ("b", _meta("b")),
        )
        selector = TieredBrickSelector(tiers=[], max_results=20)
        result = selector.select("anything", reg)
        assert len(result.list_all()) == 2


# ── TestEmbeddingTier ───────────────────────────────────────────────────────


class TestEmbeddingTier:
    """Tests for EmbeddingTier using a stub EmbeddingProvider."""

    def _make_provider(self, vecs: dict[str, list[float]]) -> EmbeddingProvider:
        """Return a stub provider that maps text → vector."""

        class StubProvider(EmbeddingProvider):
            def embed(self, texts: list[str]) -> list[list[float]]:
                return [vecs.get(t, [0.0]) for t in texts]

        return StubProvider()

    def test_cosine_similarity_used(self) -> None:
        """EmbeddingTier returns high score for similar vectors."""
        provider = self._make_provider({"task text": [1.0, 0.0], "calc add numbers": [1.0, 0.0]})
        tier = EmbeddingTier(provider, query_text="task text")
        meta = _meta("calc", description="add numbers")
        score = tier.score(BrickQuery(), "calc", meta, lambda: None)
        assert score > 0.9

    def test_empty_query_text_returns_zero(self) -> None:
        """EmbeddingTier returns 0 when query_text is empty."""
        provider = self._make_provider({})
        tier = EmbeddingTier(provider, query_text="")
        meta = _meta("brick", description="something")
        score = tier.score(BrickQuery(), "brick", meta, lambda: None)
        assert score == 0.0

    def test_invalidate_cache_resets_query_vec(self) -> None:
        """invalidate_cache() clears cached query vector."""
        call_log: list[str] = []

        class LogProvider(EmbeddingProvider):
            def embed(self, texts: list[str]) -> list[list[float]]:
                call_log.extend(texts)
                return [[1.0] for _ in texts]

        tier = EmbeddingTier(LogProvider(), query_text="task")
        meta = _meta("brick", description="brick")
        tier.score(BrickQuery(), "brick", meta, lambda: None)
        first_call_count = len(call_log)
        tier.invalidate_cache()
        tier.score(BrickQuery(), "brick", meta, lambda: None)
        # After invalidation, query text should be re-embedded
        assert len(call_log) > first_call_count
