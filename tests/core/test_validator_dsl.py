"""Tests for the Python DSL validator (AST whitelist)."""

from __future__ import annotations

from bricks.core.validator_dsl import PythonDSLValidator, ValidationResult, validate_dsl

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid(code: str) -> ValidationResult:
    return PythonDSLValidator().validate(code)


def _invalid(code: str) -> ValidationResult:
    return PythonDSLValidator().validate(code)


# ---------------------------------------------------------------------------
# Valid-code tests (10)
# ---------------------------------------------------------------------------


def test_valid_simple_step_call() -> None:
    code = """
@flow
def my_flow():
    return step.clean(text="hello")
"""
    result = _valid(code)
    assert result.valid


def test_valid_chained_step_calls() -> None:
    code = """
@flow
def my_flow():
    a = step.load(path="/data")
    b = step.clean(data=a)
    return step.save(data=b)
"""
    result = _valid(code)
    assert result.valid


def test_valid_for_each() -> None:
    code = """
@flow
def my_flow(items):
    result = for_each(items, do=lambda x: step.clean(text=x))
    return result
"""
    result = _valid(code)
    assert result.valid


def test_valid_branch() -> None:
    code = """
@flow
def my_flow():
    result = branch("check", if_true=lambda: step.a(), if_false=lambda: step.b())
    return result
"""
    result = _valid(code)
    assert result.valid


def test_valid_string_literal() -> None:
    code = """
@flow
def my_flow():
    return step.process(name="hello world", flag=True, count=42)
"""
    result = _valid(code)
    assert result.valid


def test_valid_list_and_dict_literals() -> None:
    code = """
@flow
def my_flow():
    return step.process(tags=["a", "b"], opts={"key": "val"})
"""
    result = _valid(code)
    assert result.valid


def test_valid_variable_assignment_and_reference() -> None:
    code = """
@flow
def my_flow():
    x = step.load()
    y = step.transform(data=x)
    return y
"""
    result = _valid(code)
    assert result.valid


def test_valid_none_literal() -> None:
    code = """
@flow
def my_flow():
    return step.run(value=None)
"""
    result = _valid(code)
    assert result.valid


def test_valid_complex_pipeline() -> None:
    code = """
@flow
def pipeline(data):
    loaded = step.load(path=data)
    cleaned = for_each(loaded, do=lambda x: step.clean(text=x))
    checked = branch("validate", if_true=lambda: step.approve(), if_false=lambda: step.reject())
    merged = step.merge(a=cleaned, b=checked)
    return step.save(data=merged)
"""
    result = _valid(code)
    assert result.valid


def test_valid_flow_with_docstring() -> None:
    code = '''
@flow
def my_flow():
    """This is a documented flow."""
    return step.run()
'''
    result = _valid(code)
    assert result.valid


# ---------------------------------------------------------------------------
# Invalid-code tests (15)
# ---------------------------------------------------------------------------


def test_invalid_import_statement() -> None:
    code = """
import os

@flow
def my_flow():
    return step.run()
"""
    result = _invalid(code)
    assert not result.valid
    assert any("Import" in e for e in result.errors)


def test_invalid_from_import() -> None:
    code = """
from os import path

@flow
def my_flow():
    return step.run()
"""
    result = _invalid(code)
    assert not result.valid
    assert any("Import" in e for e in result.errors)


def test_invalid_exec_call() -> None:
    code = """
@flow
def my_flow():
    exec("bad code")
    return step.run()
"""
    result = _invalid(code)
    assert not result.valid
    assert any("exec" in e for e in result.errors)


def test_invalid_eval_call() -> None:
    code = """
@flow
def my_flow():
    return eval("step.run()")
"""
    result = _invalid(code)
    assert not result.valid
    assert any("eval" in e for e in result.errors)


def test_invalid_open_call() -> None:
    code = """
@flow
def my_flow():
    f = open("secret.txt")
    return step.run()
"""
    result = _invalid(code)
    assert not result.valid
    assert any("open" in e for e in result.errors)


def test_invalid_class_definition() -> None:
    code = """
@flow
def my_flow():
    return step.run()

class Sneaky:
    pass
"""
    result = _invalid(code)
    assert not result.valid
    assert any("ClassDef" in e for e in result.errors)


def test_invalid_for_loop() -> None:
    code = """
@flow
def my_flow():
    for i in range(10):
        pass
    return step.run()
"""
    result = _invalid(code)
    assert not result.valid
    assert any("For" in e for e in result.errors)


def test_invalid_while_loop() -> None:
    code = """
@flow
def my_flow():
    while True:
        break
    return step.run()
"""
    result = _invalid(code)
    assert not result.valid
    assert any("While" in e for e in result.errors)


def test_invalid_if_statement() -> None:
    code = """
@flow
def my_flow():
    if True:
        pass
    return step.run()
"""
    result = _invalid(code)
    assert not result.valid
    assert any("If" in e for e in result.errors)


def test_invalid_try_except() -> None:
    code = """
@flow
def my_flow():
    try:
        step.run()
    except Exception:
        pass
"""
    result = _invalid(code)
    assert not result.valid
    assert any("Try" in e for e in result.errors)


def test_invalid_no_flow_decorator() -> None:
    code = """
def my_flow():
    return step.run()
"""
    result = _invalid(code)
    assert not result.valid
    assert any("@flow" in e for e in result.errors)


def test_invalid_multiple_function_definitions() -> None:
    code = """
@flow
def flow_a():
    return step.a()

@flow
def flow_b():
    return step.b()
"""
    result = _invalid(code)
    assert not result.valid
    assert any("2" in e for e in result.errors)


def test_invalid_dunder_import() -> None:
    code = """
@flow
def my_flow():
    mod = __import__("os")
    return step.run()
"""
    result = _invalid(code)
    assert not result.valid
    assert any("__import__" in e for e in result.errors)


def test_invalid_syntax_error() -> None:
    code = "def broken(:"
    result = _invalid(code)
    assert not result.valid
    assert any("Syntax" in e or "syntax" in e for e in result.errors)


def test_invalid_empty_string() -> None:
    result = _invalid("")
    assert not result.valid
    assert result.errors


# ---------------------------------------------------------------------------
# Edge-case / warning tests (3)
# ---------------------------------------------------------------------------


def test_warning_fstring() -> None:
    code = """
@flow
def my_flow(name):
    return step.greet(msg=f"hello {name}")
"""
    result = _valid(code)
    # f-strings produce a warning but do not fail validation
    assert result.valid
    assert any("f-string" in w for w in result.warnings)


def test_warning_unknown_attribute() -> None:
    code = """
@flow
def my_flow():
    return result.process()
"""
    result = _valid(code)
    # 'result' is not in ALLOWED_NAMES — should warn, not fail
    assert result.valid
    assert any("result" in w for w in result.warnings)


def test_validate_dsl_convenience_wrapper() -> None:
    code = """
@flow
def my_flow():
    return step.run()
"""
    result = validate_dsl(code)
    assert isinstance(result, ValidationResult)
    assert result.valid


# ---------------------------------------------------------------------------
# @flow(...) call syntax (Mission 072 Fix 2)
# ---------------------------------------------------------------------------


def test_validator_accepts_flow_with_kwargs() -> None:
    """@flow(outputs_map={...}) passes validator — must not raise 'decorated with @flow' error."""
    code = """
@flow(outputs_map={"active_count": "step_1.result"})
def my_flow(data):
    return step.process(data=data)
"""
    result = validate_dsl(code)
    assert result.valid, f"Expected valid, got errors: {result.errors}"
    assert not any("decorated with @flow" in e for e in result.errors)


def test_validator_accepts_bare_flow() -> None:
    """Regression guard: bare @flow still passes after adding @flow(...) support."""
    code = """
@flow
def my_flow(data):
    return step.process(data=data)
"""
    result = validate_dsl(code)
    assert result.valid, f"Bare @flow must still be valid, got: {result.errors}"
