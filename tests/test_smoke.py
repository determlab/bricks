"""End-to-end smoke test: execute a simple CRM filter blueprint deterministically."""

from __future__ import annotations

from typing import Any

# Minimal valid blueprint YAML for filtering active customers
_ACTIVE_FILTER_YAML = """\
name: filter_active_customers
description: Filter customers by status=active
inputs:
  data: []
steps:
  - name: filter
    brick: filter_dict_list
    params:
      items: "${inputs.data}"
      key: status
      value: active
    save_as: filter
outputs_map:
  active_customers: "${filter.result}"
"""

_SAMPLE_CRM_DATA = [
    {"name": "Alice", "status": "active", "plan": "pro"},
    {"name": "Bob", "status": "inactive", "plan": "basic"},
    {"name": "Carol", "status": "active", "plan": "enterprise"},
]


def test_engine_executes_prebuilt_blueprint() -> None:
    """Smoke test: engine executes a pre-built blueprint, returns active_customers."""
    from bricks.core.engine import BlueprintEngine
    from bricks.core.loader import BlueprintLoader
    from bricks.core.registry import BrickRegistry
    from bricks.stdlib import register as _reg

    registry = BrickRegistry()
    _reg(registry)
    engine = BlueprintEngine(registry=registry)
    loader = BlueprintLoader()
    bp_def = loader.load_string(_ACTIVE_FILTER_YAML)
    result = engine.run(bp_def, inputs={"data": _SAMPLE_CRM_DATA})
    active: list[dict[str, Any]] = result.outputs.get("active_customers", [])
    assert isinstance(active, list)
    assert len(active) == 2
    assert all(c["status"] == "active" for c in active)


def test_run_blueprint_public_api() -> None:
    """The top-level run_blueprint() helper covers load → validate → execute."""
    from bricks import run_blueprint

    result = run_blueprint(_ACTIVE_FILTER_YAML, inputs={"data": _SAMPLE_CRM_DATA})
    active = result.outputs["active_customers"]
    assert [c["name"] for c in active] == ["Alice", "Carol"]
