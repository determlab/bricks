"""``bricks.run_for_unit``: run a blueprint for a unit and get its verdict (#59)."""

from __future__ import annotations

import json
from pathlib import Path

from bricks import RunOutcome, build_default_registry, run_for_unit
from bricks.core.brick import brick
from bricks.core.exceptions import BrickExecutionError, GuardFailedError

_PSU = Path(__file__).resolve().parent.parent / "blueprints" / "psu_limits.yaml"

_GUARDED_YAML = (
    "name: guarded_unit\n"
    "steps:\n"
    "  - name: check\n"
    "    type: guard\n"
    "    brick: is_within\n"
    "    params: {value: 4.7, min: 4.9, max: 5.1}\n"
    '    message: "vout out of range"\n'
    "outputs_map: {}\n"
)

_MISSING_BRICK_YAML = "name: missing\nsteps:\n  - name: s\n    brick: no_such_brick\n    params: {}\noutputs_map: {}\n"


@brick()
def is_within(value: float, min: float, max: float) -> bool:
    """Return whether value is within [min, max]."""
    return min <= value <= max


def _registry_with_is_within():
    # `is_within` is not a stdlib brick — the default registry doesn't have
    # it, so `_GUARDED_YAML`'s guard step would hit BrickNotFoundError and
    # the run would read "error" instead of exercising the guard-failure
    # path this test is actually for.
    registry = build_default_registry()
    registry.register("is_within", is_within, is_within.__brick_meta__)
    return registry


def test_psu_pass() -> None:
    out = run_for_unit(_PSU, {"vout": 5.0, "iout": 0.4, "ripple_pp": 12}, unit="SN-1")
    assert isinstance(out, RunOutcome)
    assert out.verdict.status == "pass"
    assert out.unit == "SN-1"
    assert out.result is not None
    assert out.result.outputs["vout"] == 5.0


def test_psu_fail_names_vout() -> None:
    out = run_for_unit(str(_PSU), {"vout": 4.7, "iout": 0.4, "ripple_pp": 12}, unit="SN-2")
    assert out.verdict.status == "fail"
    assert out.verdict.detail is not None
    assert "vout" in out.verdict.detail
    assert out.unit == "SN-2"


def test_default_unit_is_bench() -> None:
    assert run_for_unit(_PSU, {"vout": 5.0, "iout": 0.4, "ripple_pp": 12}).unit == "bench"


def test_guard_failure_is_fail_not_raise() -> None:
    out = run_for_unit(_GUARDED_YAML, registry=_registry_with_is_within())
    assert out.verdict.status == "fail"
    assert out.result is None
    assert isinstance(out.error, GuardFailedError)


def test_missing_brick_is_error_not_raise() -> None:
    out = run_for_unit(_MISSING_BRICK_YAML)
    assert out.verdict.status == "error"
    assert out.verdict.detail


def test_wrapped_guard_failure_is_still_fail(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    guard = GuardFailedError("check", "is_within", "vout out of range", "False")
    wrapper = BrickExecutionError("is_within", "check", guard)

    def _boom(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise wrapper

    monkeypatch.setattr("bricks.outcome.BlueprintEngine.run", _boom)
    out = run_for_unit(_GUARDED_YAML)
    assert out.verdict.status == "fail"

    chained = BrickExecutionError("is_within", "check", ValueError("x"))
    chained.__cause__ = guard

    def _boom2(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise chained

    monkeypatch.setattr("bricks.outcome.BlueprintEngine.run", _boom2)
    assert run_for_unit(_GUARDED_YAML).verdict.status == "fail"


def test_missing_file_is_error_naming_the_path(tmp_path: Path) -> None:
    missing = tmp_path / "nope.yaml"
    out = run_for_unit(missing)
    assert out.verdict.status == "error"
    assert out.verdict.detail is not None
    assert str(missing) in out.verdict.detail
    assert out.result is None


def test_unreadable_path_is_error(tmp_path: Path) -> None:
    out = run_for_unit(tmp_path)  # a directory, not a file
    assert out.verdict.status == "error"
    assert str(tmp_path) in (out.verdict.detail or "")


def test_model_dump_json() -> None:
    out = run_for_unit(_PSU, {"vout": 4.7, "iout": 0.4, "ripple_pp": 12}, unit="SN-2")
    doc = json.loads(out.model_dump_json())
    assert doc["unit"] == "SN-2"
    assert doc["verdict"]["status"] == "fail"
