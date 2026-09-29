"""Tests for the check-brick checks that tests/cli/test_check_brick.py does not reach (#83).

One small bad brick per check id: meta.description, contract.inputs,
contract.run, contract.return, contract.output_keys. Each test asserts the
``Problem.check`` id and that ``fix`` names the brick.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from bricks.core.brick_check import CheckTarget, Problem, check_contract, check_meta, run_checks
from bricks.core.models import BrickMeta
from bricks.core.registry import BrickRegistry


def _only(problems: list[Problem], check: str, name: str) -> Problem:
    """The single problem in *problems*, asserted to be *check* and to name the brick in its fix."""
    assert [p.check for p in problems] == [check]
    problem = problems[0]
    assert problem.brick == name
    assert name in problem.fix
    return problem


def test_meta_description_empty() -> None:
    def no_description(n: float) -> dict[str, float]:
        return {"result": n}

    meta = BrickMeta(name="no_description", description="  ")
    problems = check_meta("no_description", no_description, meta)
    assert "meta.description" in [p.check for p in problems]
    problem = next(p for p in problems if p.check == "meta.description")
    assert "no_description" in problem.fix


def test_meta_description_empty_via_run_checks() -> None:
    def no_description(n: float) -> dict[str, float]:
        return {"result": n}

    target = CheckTarget("no_description", no_description, BrickMeta(name="no_description"))
    problems = run_checks(target, BrickRegistry())
    problem = next(p for p in problems if p.check == "meta.description")
    assert "no_description" in problem.fix


def test_contract_inputs_cannot_be_built() -> None:
    def bad_inputs(n: int) -> dict[str, int]:
        return {"result": n}

    # An unreadable signature makes the input builder raise.
    bad_inputs.__signature__ = "not a signature"  # type: ignore[attr-defined]
    _only(check_contract("bad_inputs", bad_inputs), "contract.inputs", "bad_inputs")


def test_contract_run_raises_on_example_inputs() -> None:
    def raises_on_run(n: int) -> dict[str, int]:
        raise ValueError("boom")

    problem = _only(check_contract("raises_on_run", raises_on_run), "contract.run", "raises_on_run")
    assert "ValueError" in problem.fix


def test_contract_return_is_a_list() -> None:
    def returns_list(n: int) -> Any:
        return [n]

    problem = _only(check_contract("returns_list", returns_list), "contract.return", "returns_list")
    assert "list" in problem.fix


def test_contract_output_keys_missing() -> None:
    class MissingKey:
        class Output(BaseModel):
            total: int
            count: int

        def __call__(self, n: int) -> dict[str, int]:
            return {"total": n}

    problem = _only(check_contract("missing_key", MissingKey()), "contract.output_keys", "missing_key")
    assert "count" in problem.fix
