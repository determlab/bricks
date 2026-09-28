"""run_for_unit: one public call from a blueprint and a unit to its verdict (#59)."""

from __future__ import annotations

from pathlib import Path

from bricks import RunOutcome, run_for_unit

PSU = Path(__file__).resolve().parent.parent / "blueprints" / "psu_limits.yaml"
GOOD = {"vout": 5.0, "iout": 0.4, "ripple_pp": 12}

_GUARDED = (
    "name: guarded_unit\n"
    "steps:\n"
    "  - name: check\n"
    "    type: guard\n"
    "    brick: is_within\n"
    "    params: {value: 4.7, min: 4.9, max: 5.1}\n"
    '    message: "vout out of range"\n'
    "outputs_map: {}\n"
)
_MISSING = "name: m\nsteps:\n  - name: s\n    brick: no_such_brick\n    params: {}\noutputs_map: {}\n"


def test_passing_unit() -> None:
    out = run_for_unit(PSU, GOOD, unit="SN-1")
    assert isinstance(out, RunOutcome)
    assert out.verdict.status == "pass"
    assert out.unit == "SN-1"
    assert out.result is not None


def test_failing_unit_names_vout_and_accepts_str_path() -> None:
    out = run_for_unit(str(PSU), {**GOOD, "vout": 4.7}, unit="SN-2")
    assert out.verdict.status == "fail"
    assert out.verdict.detail is not None
    assert "vout" in out.verdict.detail


def test_guard_failure_is_fail_and_does_not_raise() -> None:
    out = run_for_unit(_GUARDED)
    assert out.verdict.status == "fail"
    assert out.result is None
    assert out.unit == "bench"


def test_missing_brick_is_error_and_does_not_raise() -> None:
    out = run_for_unit(_MISSING)
    assert out.verdict.status == "error"
    assert out.result is None


def test_bad_path_is_error() -> None:
    assert run_for_unit("no/such/file.yaml").verdict.status == "error"
