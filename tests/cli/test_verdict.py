"""``bricks run``: a pass/fail verdict and ``--unit`` (#49).

Two layers: the pure derivation in ``bricks.verdict`` (a completed
``ExecutionResult`` in, a ``Verdict`` out — no CLI, no engine call), and the
CLI wiring (``--unit``, the new ``--json`` keys, the exit code, the text-mode
"Verdict: ..." line). The CLI tests run the real CLI in a fresh interpreter
from a clean temp directory, the same way ``tests/cli/test_json_output.py``
does.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from bricks.core.exceptions import BrickError, GuardFailedError
from bricks.core.models import ExecutionResult, StepResult
from bricks.verdict import derive_verdict, verdict_for_error, verdict_for_guard_failure

# --- derive_verdict / verdict_for_* — pure, no CLI, no engine --------------


def _measure_step(step_name: str, row: dict[str, Any]) -> StepResult:
    return StepResult(step_name=step_name, brick_name="measure", outputs={"result": row})


def test_derive_verdict_pass_with_no_measure_steps() -> None:
    other = StepResult(step_name="s", brick_name="divide", outputs={"result": 2.0})
    result = ExecutionResult(outputs={"x": 1}, steps=[other])
    verdict = derive_verdict(result)
    assert verdict.status == "pass"
    assert verdict.measurements == []
    assert verdict.detail is None


def test_derive_verdict_raises_loudly_on_an_empty_result() -> None:
    # An empty ``steps`` means the result was never run at STANDARD verbosity
    # (or higher) — MINIMAL discards steps outright — so there is nothing to
    # derive a verdict from. Silently reporting "pass" would be a false
    # pass; this must fail loudly instead.
    result = ExecutionResult(outputs={}, steps=[])
    with pytest.raises(ValueError, match="no steps recorded"):
        derive_verdict(result)


def test_derive_verdict_pass_with_a_passing_measurement() -> None:
    row = {"name": "vout", "value": 5.0, "unit": "V", "limits": {"min": 4.9, "max": 5.1}, "pass": True}
    result = ExecutionResult(outputs={}, steps=[_measure_step("vout", row)])
    verdict = derive_verdict(result)
    assert verdict.status == "pass"
    assert verdict.measurements == [{"step": "vout", **row}]
    assert verdict.detail is None


def test_derive_verdict_fail_on_one_failing_measurement() -> None:
    row = {"name": "vout", "value": 4.7, "unit": "V", "limits": {"min": 4.9, "max": 5.1}, "pass": False}
    result = ExecutionResult(outputs={}, steps=[_measure_step("vout", row)])
    verdict = derive_verdict(result)
    assert verdict.status == "fail"
    assert verdict.measurements == [{"step": "vout", **row}]
    assert verdict.detail == "vout 4.7 V not in [4.9, 5.1]"


def test_derive_verdict_lists_every_row_but_details_the_first_failure() -> None:
    passing = {"name": "iin", "value": 1.0, "unit": "A", "limits": {}, "pass": True}
    failing_first = {"name": "vout", "value": 4.7, "unit": "V", "limits": {"min": 4.9, "max": 5.1}, "pass": False}
    failing_second = {"name": "vref", "value": 0.5, "unit": "V", "limits": {"min": 0.9}, "pass": False}
    result = ExecutionResult(
        outputs={},
        steps=[
            _measure_step("iin", passing),
            _measure_step("vout", failing_first),
            _measure_step("vref", failing_second),
        ],
    )
    verdict = derive_verdict(result)
    assert verdict.status == "fail"
    assert verdict.measurements == [
        {"step": "iin", **passing},
        {"step": "vout", **failing_first},
        {"step": "vref", **failing_second},
    ]
    assert verdict.detail == "vout 4.7 V not in [4.9, 5.1]"


def test_derive_verdict_ignores_steps_that_are_not_measure() -> None:
    other = StepResult(step_name="s", brick_name="divide", outputs={"result": 2.0})
    result = ExecutionResult(outputs={}, steps=[other])
    verdict = derive_verdict(result)
    assert verdict.status == "pass"
    assert verdict.measurements == []


def test_verdict_for_guard_failure_is_fail_with_a_one_line_detail_and_no_measurements() -> None:
    exc = GuardFailedError(step_name="check", brick_name="is_within", message="vout out of range", actual="False")
    verdict = verdict_for_guard_failure(exc)
    assert verdict.status == "fail"
    assert verdict.measurements == []
    assert verdict.detail == "Guard 'check' failed: vout out of range"


def test_verdict_for_error_is_error_with_no_measurements() -> None:
    exc = BrickError("boom")
    verdict = verdict_for_error(exc)
    assert verdict.status == "error"
    assert verdict.measurements == []
    assert verdict.detail == "boom"


# --- CLI: --unit, exit code, --json keys, the text-mode Verdict line -------

_LIB_QA = (
    "from bricks.core import brick\n\n\n"
    "@brick()\n"
    "def is_within(value: float, min: float, max: float) -> bool:\n"
    '    """Return whether value is within [min, max]."""\n'
    "    return min <= value <= max\n\n\n"
    "@brick()\n"
    "def boom() -> dict[str, int]:\n"
    '    """Always raise, to exercise the CLI\'s generic BrickError path."""\n'
    '    raise ValueError("power supply exploded")\n'
)

_PSU_PASS_YAML = (
    "name: psu_pass\n"  # noqa: S105
    "steps:\n"
    "  - name: vout\n"
    "    brick: measure\n"
    '    params: {name: vout, value: 5.0, unit: "V", min: 4.9, max: 5.1}\n'
    "    save_as: m\n"
    "outputs_map:\n"
    '  vout: "${m.result.value}"\n'
)

# Values chosen to match the exact JSON example in the issue: unit SN-2,
# vout 4.7 V outside [4.9, 5.1].
_PSU_LIMITS_YAML = (
    "name: psu_limits\n"
    "inputs:\n"
    '  vout_value: "float"\n'
    "steps:\n"
    "  - name: vout\n"
    "    brick: measure\n"
    "    params:\n"
    "      name: vout\n"
    '      value: "${vout_value}"\n'
    '      unit: "V"\n'
    "      min: 4.9\n"
    "      max: 5.1\n"
    "    save_as: m\n"
    "outputs_map:\n"
    '  vout: "${m.result.value}"\n'
)

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

_ERRORING_YAML = "name: erroring_unit\nsteps:\n  - name: boom_step\n    brick: boom\n    params: {}\noutputs_map: {}\n"


def _bricks(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the ``bricks`` CLI in a fresh interpreter, stdout and stderr decoded as UTF-8."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(  # noqa: S603  — fixed argv: this interpreter + a literal snippet + test args
        [sys.executable, "-c", "from bricks.cli.main import app; app(prog_name='bricks')", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )


def _one_json(result: subprocess.CompletedProcess[str]) -> Any:
    """Parse stdout as exactly one JSON document."""
    return json.loads(result.stdout)


@pytest.fixture
def work(tmp_path: Path) -> Path:
    """A directory with the ``measure``/guard/error fixture blueprints and a local lib."""
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "qa.py").write_text(_LIB_QA)
    (tmp_path / "bricks.config.yaml").write_text("registry:\n  auto_discover: true\n  paths:\n    - 'lib/'\n")
    (tmp_path / "psu_pass.yaml").write_text(_PSU_PASS_YAML)
    (tmp_path / "psu_limits.yaml").write_text(_PSU_LIMITS_YAML)
    (tmp_path / "guarded.yaml").write_text(_GUARDED_YAML)
    (tmp_path / "erroring.yaml").write_text(_ERRORING_YAML)
    return tmp_path


# --- pass ---------------------------------------------------------------


def test_run_json_pass_defaults_unit_to_bench(work: Path) -> None:
    result = _bricks(work, "run", "psu_pass.yaml", "--json")
    assert result.returncode == 0, result.stderr
    assert _one_json(result) == {
        "ok": True,
        "blueprint": "psu_pass",
        "unit": "bench",
        "verdict": "pass",
        "measurements": [
            {
                "step": "vout",
                "name": "vout",
                "value": 5.0,
                "unit": "V",
                "limits": {"min": 4.9, "max": 5.1},
                "pass": True,
            }
        ],
        "outputs": {"vout": 5.0},
    }


def test_run_text_pass_prints_verdict_line_with_default_unit(work: Path) -> None:
    result = _bricks(work, "run", "psu_pass.yaml")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[-1] == "Verdict: PASS (unit bench)"


# --- one failing measure --------------------------------------------------


def test_run_json_failing_measurement_matches_the_issue_example(work: Path) -> None:
    result = _bricks(work, "run", "psu_limits.yaml", "-i", "vout_value=4.7", "--unit", "SN-2", "--json")
    assert result.returncode == 1
    assert _one_json(result) == {
        "ok": True,
        "blueprint": "psu_limits",
        "unit": "SN-2",
        "verdict": "fail",
        "measurements": [
            {
                "step": "vout",
                "name": "vout",
                "value": 4.7,
                "unit": "V",
                "limits": {"min": 4.9, "max": 5.1},
                "pass": False,
            }
        ],
        "outputs": {"vout": 4.7},
    }


def test_run_text_failing_measurement_matches_the_issue_example(work: Path) -> None:
    result = _bricks(work, "run", "psu_limits.yaml", "-i", "vout_value=4.7", "--unit", "SN-2")
    assert result.returncode == 1
    assert result.stdout.splitlines()[-1] == "Verdict: FAIL (unit SN-2): vout 4.7 V not in [4.9, 5.1]"


# --- a failed guard --------------------------------------------------------


def test_run_json_guard_failure_is_ok_true_verdict_fail(work: Path) -> None:
    result = _bricks(work, "run", "guarded.yaml", "--json")
    assert result.returncode == 1
    assert _one_json(result) == {
        "ok": True,
        "blueprint": "guarded_unit",
        "unit": "bench",
        "verdict": "fail",
        "measurements": [],
        "outputs": {},
    }


def test_run_text_guard_failure_prints_verdict_fail_and_no_traceback(work: Path) -> None:
    """A GuardFailedError used to traceback in text mode; it must not any more."""
    result = _bricks(work, "run", "guarded.yaml")
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert result.stdout.strip() == "Verdict: FAIL (unit bench): Guard 'check' failed: vout out of range"


# --- a brick error -----------------------------------------------------


def test_run_json_brick_error_is_ok_false_verdict_error(work: Path) -> None:
    result = _bricks(work, "run", "erroring.yaml", "--json")
    assert result.returncode == 1
    doc = _one_json(result)
    assert doc["ok"] is False
    assert doc["unit"] == "bench"
    assert doc["verdict"] == "error"
    assert doc["error"]["type"] == "BrickExecutionError"
    assert doc["error"]["step"] == "boom_step"
    assert doc["error"]["brick"] == "boom"


def test_run_text_brick_error_prints_verdict_error_line(work: Path) -> None:
    result = _bricks(work, "run", "erroring.yaml")
    assert result.returncode == 1
    assert result.stdout == ""
    lines = result.stderr.strip("\n").splitlines()
    assert lines[0] == "Execution error: Brick 'boom' failed at step 'boom_step': power supply exploded"
    assert lines[1] == "Verdict: ERROR (unit bench): Brick 'boom' failed at step 'boom_step': power supply exploded"


# --- exit codes --------------------------------------------------------


@pytest.mark.parametrize(
    ("blueprint", "extra_args", "expected_code"),
    [
        ("psu_pass.yaml", [], 0),
        ("psu_limits.yaml", ["-i", "vout_value=4.7"], 1),
        ("guarded.yaml", [], 1),
        ("erroring.yaml", [], 1),
    ],
)
def test_exit_code_is_0_on_pass_1_otherwise(
    work: Path, blueprint: str, extra_args: list[str], expected_code: int
) -> None:
    assert _bricks(work, "run", blueprint, *extra_args, "--json").returncode == expected_code
    assert _bricks(work, "run", blueprint, *extra_args).returncode == expected_code


# --- the same blueprint, two units -----------------------------------------


def test_run_twice_with_different_units_gives_different_unit_and_matching_verdict(work: Path) -> None:
    sn1 = _bricks(work, "run", "psu_limits.yaml", "-i", "vout_value=5.0", "--unit", "SN-1", "--json")
    sn2 = _bricks(work, "run", "psu_limits.yaml", "-i", "vout_value=4.7", "--unit", "SN-2", "--json")
    assert sn1.returncode == 0, sn1.stderr
    assert sn2.returncode == 1
    doc1, doc2 = _one_json(sn1), _one_json(sn2)
    assert doc1["unit"] == "SN-1"
    assert doc2["unit"] == "SN-2"
    assert doc1["unit"] != doc2["unit"]
    assert doc1["verdict"] == "pass"
    assert doc2["verdict"] == "fail"


def test_public_api() -> None:
    from bricks import derive_verdict  # noqa: F401
