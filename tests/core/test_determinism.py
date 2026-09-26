"""D1: the same blueprint and the same inputs produce the same outputs, every run.

G3 in ``docs/DECISIONS.md`` records that nothing tested this. The first test
runs one blueprint twice through the public entry point and compares both the
``ExecutionResult.outputs`` and the bytes they render to.

No shipped blueprint uses ``__for_each__`` (``examples/daily-summary.yaml``,
named in #32, does not exist in this tree), so the blueprint below is the
smallest one that does: parse, project, then map a brick over a list.

The second test proves the comparison can fail. ``now_timestamp`` reads the
clock (G1), so two runs that see different instants give different outputs.
The test drives the clock the brick reads instead of sleeping across a real
second, so it cannot be flaky: the brick's own code runs unchanged, and only
the value ``datetime.now`` returns is controlled.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

import bricks.stdlib.date_time as date_time_module
from bricks.api import build_default_registry, run_blueprint
from bricks.core.models import ExecutionResult

FOR_EACH_BLUEPRINT = """\
name: determinism_for_each
description: "Parse a JSON list, take each name, hash every name."
inputs:
  people_json: "str"
steps:
  - name: parse
    brick: extract_json_from_str
    params:
      text: "${people_json}"
    save_as: parsed

  - name: names
    brick: map_values
    params:
      items: "${parsed.result}"
      key: "name"
    save_as: names

  - name: hash_each
    brick: __for_each__
    params:
      items: "${names.result}"
      do_brick: compute_hash
      item_kwarg: data
    save_as: hashed

outputs_map:
  names: "${names.result}"
  hashes: "${hashed.result}"
"""

CLOCK_BLUEPRINT = """\
name: determinism_clock
description: "Read the current UTC time."
steps:
  - name: stamp
    brick: now_timestamp
    save_as: stamp

outputs_map:
  stamp: "${stamp.result}"
"""

PEOPLE_JSON = json.dumps(
    [
        {"name": "Ada", "role": "eng"},
        {"name": "Zoë", "role": "ops"},
        {"name": "Ada", "role": "pm"},
    ]
)


def _render(result: ExecutionResult) -> bytes:
    """Render outputs to bytes as a caller would write them out.

    ``sort_keys`` is off on purpose: a change in key order is a change in
    the bytes a caller sees, so it must count as a difference.
    """
    return json.dumps(result.outputs, ensure_ascii=False).encode("utf-8")


def test_for_each_blueprint_run_twice_is_byte_identical() -> None:
    """D1: two runs, identical inputs -> equal outputs and identical bytes."""
    registry = build_default_registry()

    first = run_blueprint(FOR_EACH_BLUEPRINT, inputs={"people_json": PEOPLE_JSON}, registry=registry)
    second = run_blueprint(FOR_EACH_BLUEPRINT, inputs={"people_json": PEOPLE_JSON}, registry=registry)

    # The run did real work, so equality below is not two empty dicts agreeing.
    assert first.outputs["names"] == ["Ada", "Zoë", "Ada"], first.outputs
    assert len(first.outputs["hashes"]) == 3, first.outputs
    assert first.outputs["hashes"][0] == first.outputs["hashes"][2], "same name must hash the same"

    assert first.outputs == second.outputs, (first.outputs, second.outputs)
    assert _render(first) == _render(second), (_render(first), _render(second))


class _SteppingClock(datetime):
    """A ``datetime`` whose ``now`` returns one second later on each call."""

    _ticks: Iterator[datetime]

    @classmethod
    def now(cls, tz: Any = None) -> _SteppingClock:  # type: ignore[override]
        instant = next(cls._ticks)
        return cls.fromtimestamp(instant.timestamp(), tz=tz)


def test_clock_blueprint_run_twice_is_not_identical(monkeypatch: pytest.MonkeyPatch) -> None:
    """D1's comparison can fail: a brick that reads the clock differs across runs (G1).

    Without this, the test above could pass because the comparison is blind.
    """
    start = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    _SteppingClock._ticks = (start + timedelta(seconds=n) for n in range(10))
    monkeypatch.setattr(date_time_module, "datetime", _SteppingClock)
    registry = build_default_registry()

    first = run_blueprint(CLOCK_BLUEPRINT, registry=registry)
    second = run_blueprint(CLOCK_BLUEPRINT, registry=registry)

    # The brick read the controlled clock, once per run.
    assert first.outputs == {"stamp": "2026-01-01T12:00:00"}, first.outputs
    assert second.outputs == {"stamp": "2026-01-01T12:00:01"}, second.outputs

    assert first.outputs != second.outputs
    assert _render(first) != _render(second)
