"""Selector measurement: the full 101-brick registry vs the 14-brick common set.

`ops/projects/shal/specs/tool-set.md` R6 and `ops/projects/bricks/specs/block-set.md`
both say the same thing: the "sweet spot 12-16, ceiling 20" range is borrowed
evidence, and it must be measured on *this* catalog before anything is built on
it. This module is that measurement.

What it measures
----------------
The selector under test is :class:`~bricks.core.catalog.TieredCatalog`:

* **Tier 1** — :meth:`~bricks.core.catalog.TieredCatalog.list_bricks` returns the
  configured ``common_set`` (``CatalogConfig.common_set``) plus the session cache.
* **Tier 2** — :meth:`~bricks.core.catalog.TieredCatalog.lookup_brick` is a
  case-insensitive substring search over every brick's name, description and tags.

The same 30-task set is run twice against a real stdlib registry:

* ``full``   — ``common_set`` is every registered brick, so Tier 1 lists all 101.
* ``common`` — ``common_set`` is the 14 names ``block-set.md`` marks
  "Keep visible, unchanged".

What it deliberately does **not** measure
-----------------------------------------
There is no model in this loop, so this is not a measurement of *selection
accuracy*. It cannot locate a degradation curve and it cannot confirm or refute
"12-16" as a sweet spot — that needs a model choosing under both listings.

What it does measure is the thing the selector actually controls: how much of the
catalog a caller is shown, whether the right brick is in that listing, how many
same-keyword rivals sit beside it, and whether one Tier-2 search recovers a miss.
The `full` hit-rate is 100% by construction (everything is listed); precision
there is by construction too, since every task has exactly one expected brick,
so mean precision is exactly 1 / listing-size (0.0099 = 1/101, 0.0714 = 1/14) -
it just restates how big the listing is. The rival count is the informative
number.

Runtime is well under a second, so this runs in the default suite with no marker
and CI's existing `pytest` step picks it up.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pytest

from bricks.core.catalog import TieredCatalog
from bricks.core.registry import BrickRegistry
from bricks.stdlib import register

BASELINE_PATH = Path(__file__).resolve().parents[1] / "baselines" / "selector_measurement.md"

#: The 14 names ``block-set.md`` lists under "Keep visible, unchanged" — the
#: candidate value for ``CatalogConfig.common_set``. Taken verbatim from the
#: spec, in the spec's own order. The seven bricks the spec proposes to *build*
#: (``render_template``, ``render_each``, ``join_text``, ``select_where``,
#: ``date_window``, ``take``, ``default_if_empty``) do not exist yet and are
#: therefore not part of this measurement.
COMMON_SET: tuple[str, ...] = (
    "sort_dict_list",
    "map_values",
    "group_by_key",
    "calculate_aggregates",
    "extract_json_from_str",
    "select_dict_keys",
    "merge_dictionaries",
    "add_days",
    "date_diff",
    "compare_values",
    "is_not_empty",
    "unique_values",
    "round_number",
    "percentage",
)


@dataclass(frozen=True)
class Task:
    """One measurement task.

    Attributes:
        task_id: Stable identifier used in the baseline file.
        prompt: How a person would ask for this, in natural language.
        query: The Tier-2 search term. **Rule: a single word the prompt itself
            uses.** Not reverse-engineered from the expected brick name — a query
            tuned to the answer would measure the author, not the selector.
        expected: The brick(s) that genuinely answer the prompt, verified against
            the live registry by :func:`test_every_expected_brick_exists`.
    """

    task_id: str
    prompt: str
    query: str
    expected: tuple[str, ...]


#: Thirty tasks across all seven stdlib categories. Fourteen have an answer
#: inside the common set and sixteen do not — the second half is the point, since
#: a task set that only asks what the small config already knows proves nothing.
TASKS: tuple[Task, ...] = (
    # ── answers that live inside the common set ──────────────────────────────
    Task("T01", "Sort the day's calendar events by start time.", "sort", ("sort_dict_list",)),
    Task("T02", "Pull the title field out of each event record.", "field", ("map_values",)),
    Task("T03", "Group this week's expenses by category.", "group", ("group_by_key",)),
    Task("T04", "Add up the total amount across a list of invoice records.", "total", ("calculate_aggregates",)),
    Task("T05", "The reply had JSON inside a markdown fence - get the object out.", "json", ("extract_json_from_str",)),
    Task("T06", "Keep only the name and email keys of a contact record.", "keys", ("select_dict_keys",)),
    Task("T07", "Merge the default settings with the user's overrides.", "merge", ("merge_dictionaries",)),
    Task("T08", "What date is seven days after 2026-03-01?", "days", ("add_days",)),
    Task("T09", "How many days lie between the invoice date and the due date?", "between", ("date_diff",)),
    Task("T10", "Check whether the order total is greater than 500.", "greater", ("compare_values",)),
    Task("T11", "Stop the run when today's event list came back empty.", "empty", ("is_not_empty",)),
    Task("T12", "Remove repeated tags from a list, keeping the original order.", "repeated", ("unique_values",)),
    Task("T13", "Round the average to two decimal places.", "round", ("round_number",)),
    Task("T14", "What share of the tasks were completed, as a percent?", "percent", ("percentage",)),
    # ── answers that do not ──────────────────────────────────────────────────
    Task("T15", "Turn a list of rows into a CSV string to attach to the mail.", "csv", ("convert_to_csv_str",)),
    Task("T16", "Strip the HTML tags out of the fetched article body.", "html", ("remove_html_tags",)),
    Task("T17", "Shorten a headline that runs past 80 characters.", "characters", ("truncate_text",)),
    Task("T18", "Percent-encode a search term before putting it in a URL.", "encode", ("url_encode",)),
    Task("T19", "Split a long list of items into chunks of twenty.", "chunk", ("chunk_list",)),
    Task("T20", "Take only the first five entries of the list.", "first", ("take_first_n",)),
    Task("T21", "Redact addresses and phone numbers from the ticket text.", "redact", ("redact_pii_patterns",)),
    Task("T22", "Is 2026-03-14 a business day?", "business", ("is_business_day",)),
    Task("T23", "Fill a message template with the values I just computed.", "template", ("template_string_fill",)),
    Task("T24", "Join the summary lines into one block of text.", "join", ("concatenate_strings",)),
    Task("T25", "Drop duplicate records that share the same id.", "duplicate", ("deduplicate_dict_list",)),
    Task("T26", "Filter the orders down to the ones whose status is 'open'.", "filter", ("filter_dict_list",)),
    Task("T27", "Pull every URL out of the newsletter text.", "url", ("extract_urls",)),
    Task("T28", "Get the year and the month out of an ISO date.", "date", ("extract_date_parts",)),
    Task("T29", "Clamp the score so it stays between 0 and 100.", "clamp", ("clamp_value",)),
    Task("T30", "Check the address the user typed is a valid email.", "email", ("is_email_valid",)),
)


# ── Measurement ───────────────────────────────────────────────────────────────


def _stdlib_registry() -> BrickRegistry:
    """A registry holding the whole stdlib — the real 101, not stubs."""
    registry = BrickRegistry()
    register(registry)
    return registry


@dataclass(frozen=True)
class Outcome:
    """What one configuration did on one task.

    Attributes:
        listed: How many bricks Tier 1 put in front of the caller.
        hit: Whether every expected brick was in that Tier-1 listing.
        rivals: Bricks in the listing that also match the task's own query word
            but are not an expected answer — the same-keyword confusion load.
        searched: How many bricks the Tier-2 search returned.
        search_found_expected: Whether the Tier-2 search alone returned every
            expected brick. Independent of the listing, so it is the same for
            both configurations — it measures the search, not the tier-1 size.
        candidates: Size of listing + search results, i.e. everything the caller
            would have to choose between to answer this task in two steps.
        hit_after_search: Whether every expected brick was reachable in two steps.
    """

    listed: int
    hit: bool
    rivals: int
    searched: int
    search_found_expected: bool
    candidates: int
    hit_after_search: bool


def _run(registry: BrickRegistry, common_set: tuple[str, ...], task: Task) -> Outcome:
    """Run one task against one catalog configuration.

    A fresh :class:`TieredCatalog` per task keeps the Tier-3 session cache from
    leaking one task's search results into the next task's listing.
    """
    catalog = TieredCatalog(registry=registry, common_set=list(common_set))
    listed = {b["name"] for b in catalog.list_bricks()}
    expected = set(task.expected)
    found = {b["name"] for b in catalog.lookup_brick(task.query)}
    return Outcome(
        listed=len(listed),
        hit=expected <= listed,
        rivals=len((found & listed) - expected),
        searched=len(found),
        search_found_expected=expected <= found,
        candidates=len(listed | found),
        hit_after_search=expected <= (listed | found),
    )


def _percent(hits: int, total: int) -> str:
    """Format a hit count as ``n/total = xx.x%``."""
    return f"{hits}/{total} = {100.0 * hits / total:.1f}%"


def _mean_precision(outcomes: list[Outcome]) -> float:
    """Mean of ``expected / listed``. Every task has one expected brick, so this
    is exactly ``1 / listed`` by construction — it restates the listing size,
    not a discovered signal-to-noise ratio."""
    pairs = zip(TASKS, outcomes, strict=True)
    return sum(len(t.expected) / o.listed for t, o in pairs) / len(outcomes)


def build_report() -> str:
    """Run both configurations over the whole task set and render the baseline."""
    registry = _stdlib_registry()
    all_names = tuple(sorted(name for name, _ in registry.list_all()))
    configs = (("full registry", all_names), ("common set", COMMON_SET))

    results: dict[str, list[Outcome]] = {label: [_run(registry, cs, t) for t in TASKS] for label, cs in configs}
    total = len(TASKS)

    lines: list[str] = [
        "# Selector measurement: 101 bricks vs 14 (Auto-Generated)",
        "",
        "Do not hand-edit. Regenerate with:",
        "",
        "    BRICKS_UPDATE_BASELINE=1 python -m pytest tests/core/test_selector_measurement.py",
        "",
        "Produced by `tests/core/test_selector_measurement.py`, which is also where the",
        "task set, the metric definitions and the limits of this measurement are written",
        "down. Short version: there is no model in this loop, so this measures what the",
        "caller is *shown*, not what a model would *pick*. The full-registry hit-rate is",
        "100% by construction, and so is its precision (1 / listing-size, since each",
        "task has one expected brick) - the rival count is the informative number.",
        "",
        "## Configurations",
        "",
        f"- **full registry** - `CatalogConfig.common_set` = all {len(all_names)} registered bricks.",
        f"- **common set** - `CatalogConfig.common_set` = the {len(COMMON_SET)} names `block-set.md`",
        '  lists under "Keep visible, unchanged".',
        "",
        "## Summary",
        "",
        "| metric | full registry | common set |",
        "| --- | --- | --- |",
    ]

    def row(name: str, fmt) -> str:  # type: ignore[no-untyped-def]
        return f"| {name} | {fmt(results['full registry'])} | {fmt(results['common set'])} |"

    lines += [
        row("bricks listed (tier 1)", lambda rs: f"{rs[0].listed}"),
        row("tier-1 hit-rate", lambda rs: _percent(sum(r.hit for r in rs), total)),
        row("tier-1 precision (mean)", lambda rs: f"{_mean_precision(rs):.4f}"),
        row("same-keyword rivals in the listing (mean)", lambda rs: f"{sum(r.rivals for r in rs) / total:.2f}"),
        row("hit-rate after one tier-2 search", lambda rs: _percent(sum(r.hit_after_search for r in rs), total)),
        row("candidates to choose between (mean)", lambda rs: f"{sum(r.candidates for r in rs) / total:.1f}"),
        row("worst-case two-step candidates", lambda rs: f"{max(r.candidates for r in rs)}"),
        "",
        "The common-set tier-1 hit-rate (14/30 = 46.7%) is by construction as well:",
        "the 14 inside tasks are exactly one task per `common_set` brick, so this is",
        "the task mix restated, not a discovered rate.",
        "",
        "Tier 2 is the same search in both configurations, so it has one number:",
        "the query returned every expected brick on "
        f"{_percent(sum(r.search_found_expected for r in results['common set']), total)} of tasks.",
        "The tasks where it did not are recorded below; each of those happens to be",
        "answerable from tier 1 in the common-set configuration, which is why the",
        "two-step hit-rate is unaffected. It would not be, if those bricks were hidden.",
        "",
        "Two tasks have a second equally correct answer not counted above: T11",
        "(`is_not_empty`) is also answered, inverted, by `is_empty_list`; T17",
        "(`truncate_text`) names the same job as `truncate_string`, the pair",
        "`block-set.md` calls a coin-flip. Expected answers are unchanged.",
        "",
        "## Per task",
        "",
    ]

    for i, task in enumerate(TASKS):
        full, common = results["full registry"][i], results["common set"][i]
        lines += [
            f"### {task.task_id} - {task.prompt}",
            "",
            f"- expected: `{'`, `'.join(task.expected)}`",
            f'- tier-2 query: "{task.query}" - {full.searched} of {len(all_names)} bricks match it, '
            f"expected brick {'found' if full.search_found_expected else 'NOT FOUND'}",
            f"- full registry: tier-1 {'HIT ' if full.hit else 'MISS'} "
            f"- {full.listed} listed, {full.rivals} same-keyword rival(s) listed "
            f"- two-step {'HIT' if full.hit_after_search else 'MISS'} over {full.candidates} candidates",
            f"- common set:   tier-1 {'HIT ' if common.hit else 'MISS'} "
            f"- {common.listed} listed, {common.rivals} same-keyword rival(s) listed "
            f"- two-step {'HIT' if common.hit_after_search else 'MISS'} over {common.candidates} candidates",
            "",
        ]

    return "\n".join(lines).rstrip() + "\n"


# ── The experiment's own guardrails ───────────────────────────────────────────


def test_every_expected_brick_exists() -> None:
    """A task whose 'correct' answer is not a real brick would void the result."""
    registry = _stdlib_registry()
    missing = sorted({b for t in TASKS for b in t.expected if not registry.has(b)})
    assert not missing, f"tasks name bricks that are not registered: {missing}"


def test_common_set_is_fourteen_real_bricks() -> None:
    """`TieredCatalog` silently drops unknown names, so a typo would shrink the set."""
    registry = _stdlib_registry()
    assert len(COMMON_SET) == 14, f"block-set.md keeps 14 visible, got {len(COMMON_SET)}"
    missing = sorted(n for n in COMMON_SET if not registry.has(n))
    assert not missing, f"common_set names bricks that are not registered: {missing}"


def test_registry_is_still_one_hundred_and_one() -> None:
    """The 101 in the spec is the population under test; if it moves, so does the result."""
    assert len(_stdlib_registry().list_all()) == 101


def test_task_set_covers_both_directions() -> None:
    """Half the tasks must be answerable from the common set and half must not."""
    inside = [t for t in TASKS if set(t.expected) <= set(COMMON_SET)]
    outside = [t for t in TASKS if not set(t.expected) & set(COMMON_SET)]
    assert len(inside) >= 12, f"only {len(inside)} tasks are answerable from the common set"
    assert len(outside) >= 12, f"only {len(outside)} tasks are outside the common set"
    assert len(inside) + len(outside) == len(TASKS)


def test_queries_are_single_words_the_prompt_uses() -> None:
    """The query rule, enforced: a query tuned to the answer would measure nothing.

    The rule makes tier-2 recovery a *best case* — a real caller may search a word
    the catalog does not use, and three of these thirty do exactly that. But the
    bigger reason it is a best case: in 14 of the 16 outside tasks, the query
    word is also a literal substring of the expected brick's own name (e.g. T15
    "csv" / `convert_to_csv_str`, T20 "first" / `take_first_n`). The prompts were
    written in the bricks' own vocabulary, and this rule cannot catch that — it
    only checks that the query is a single word taken from the prompt. It is
    still the right bias here, because the number under test is the tier-1
    hit-rate and the query must not quietly favour either configuration.
    """
    offenders = [t.task_id for t in TASKS if t.query.lower() not in t.prompt.lower() or " " in t.query]
    assert not offenders, f"tier-2 query is not a single word from the prompt: {offenders}"


# ── The measurement ───────────────────────────────────────────────────────────


def test_baseline_is_current() -> None:
    """The recorded baseline matches what the selector does today.

    Set ``BRICKS_UPDATE_BASELINE=1`` to rewrite it. A diff here is the signal
    this whole issue exists to produce: it means the selector, the registry or
    the common set moved, and the number in `tool-set.md` §2 moved with it.
    """
    report = build_report()
    if os.environ.get("BRICKS_UPDATE_BASELINE"):
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Explicit LF: regenerating on Windows must not produce a whole-file diff.
        # Reading back uses universal newlines, so the comparison below is
        # line-ending agnostic whichever platform checked the file out.
        with BASELINE_PATH.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(report)
        pytest.skip(f"baseline rewritten: {BASELINE_PATH}")
    assert BASELINE_PATH.exists(), f"missing baseline; regenerate with BRICKS_UPDATE_BASELINE=1 ({BASELINE_PATH})"
    recorded = BASELINE_PATH.read_text(encoding="utf-8")
    assert report == recorded, (
        "selector measurement no longer matches the recorded baseline. "
        "If the change is intended, regenerate with BRICKS_UPDATE_BASELINE=1 and say so in the PR."
    )


def test_headline_numbers() -> None:
    """The two numbers the issue asks for, asserted where a reader will see them.

    Full registry lists all 101 and therefore hits every task; the common set
    lists 14 and hits fewer than half. Neither number is a surprise — the point
    is the pair, and the cost column beside it.
    """
    registry = _stdlib_registry()
    all_names = tuple(sorted(name for name, _ in registry.list_all()))

    full = [_run(registry, all_names, t) for t in TASKS]
    common = [_run(registry, COMMON_SET, t) for t in TASKS]

    assert sum(r.hit for r in full) == 30, "full registry lists everything, so it cannot miss"
    assert sum(r.hit for r in common) == 14, "14 of 30 tasks have an answer inside the common set"

    # The cost of that recall: at 101 the caller reads 7.2x more of the catalog
    # and sits beside far more same-keyword rivals.
    assert full[0].listed == 101
    assert common[0].listed == 14
    assert sum(r.rivals for r in full) > 4 * sum(r.rivals for r in common)


def test_tier_two_recovers_every_tier_one_miss() -> None:
    """The small set's misses are one search away — that is what makes 14 defensible."""
    registry = _stdlib_registry()
    common = [_run(registry, COMMON_SET, t) for t in TASKS]
    missed = [r for r in common if not r.hit]
    assert len(missed) == 16
    assert all(r.hit_after_search for r in missed), "a tier-1 miss must be recoverable in one search"
    assert sum(r.hit_after_search for r in common) == 30


def test_a_broad_query_pushes_the_two_step_surface_past_the_ceiling() -> None:
    """Recorded, not fixed: tier 2 is unbounded, so step two can undo step one.

    `tool-set.md` R1 caps a model-facing listing at 20. Tier 1 at 14 respects it,
    but `lookup_brick` returns every substring match with no cap, so a broad query
    ("date" matches 19 of 101) hands back a combined surface of 31 — above the
    ceiling the small common set was chosen to hold. The ceiling therefore has to
    apply to the search result too, not only to the listing. Out of scope here
    (this issue is test-only and `src/` must not move); worth R2/R3 knowing.
    """
    registry = _stdlib_registry()
    common = [_run(registry, COMMON_SET, t) for t in TASKS]
    worst = max(common, key=lambda r: r.candidates)
    assert worst.candidates == 31
    assert worst.candidates > 20, "if this ever drops under 20, the finding above is stale"


def test_tier_two_cannot_answer_a_multi_word_query() -> None:
    """A recorded limit of the thing measured, not a bug this issue may fix.

    ``lookup_brick`` is a substring match, so "url encode" matches nothing even
    though "url" and "encode" each match four bricks. Every query in ``TASKS`` is
    a single word for exactly this reason; a reader comparing the two hit-rates
    should know the recovery path is this literal.
    """
    catalog = TieredCatalog(registry=_stdlib_registry(), common_set=list(COMMON_SET))
    assert catalog.lookup_brick("url encode") == []
    assert len(catalog.lookup_brick("url")) == 4
    assert len(catalog.lookup_brick("encode")) == 4
