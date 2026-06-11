"""Tests for bricks.core.exceptions."""

from __future__ import annotations

import pytest

from bricks.core.exceptions import (
    BlueprintValidationError,
    BrickError,
    BrickExecutionError,
    BrickNotFoundError,
    ConfigError,
    DuplicateBrickError,
    VariableResolutionError,
    YamlLoadError,
)


class TestBrickError:
    def test_is_exception(self) -> None:
        err = BrickError("base error")
        assert isinstance(err, Exception), f"Expected Exception, got {type(err).__name__}"

    def test_message(self) -> None:
        err = BrickError("something went wrong")
        assert "something went wrong" in str(err), f"Expected 'something went wrong' in {str(err)!r}"


class TestDuplicateBrickError:
    def test_inherits_brick_error(self) -> None:
        err = DuplicateBrickError("my_brick")
        assert isinstance(err, BrickError), f"Expected BrickError, got {type(err).__name__}"

    def test_message_contains_name(self) -> None:
        err = DuplicateBrickError("my_brick")
        assert "my_brick" in str(err), f"Expected 'my_brick' in {str(err)!r}"

    def test_name_attribute(self) -> None:
        err = DuplicateBrickError("my_brick")
        assert err.name == "my_brick", f"Expected 'my_brick', got {err.name!r}"

    def test_different_name(self) -> None:
        err = DuplicateBrickError("other_brick")
        assert err.name == "other_brick", f"Expected 'other_brick', got {err.name!r}"
        assert "other_brick" in str(err), f"Expected 'other_brick' in {str(err)!r}"


class TestBrickNotFoundError:
    def test_inherits_brick_error(self) -> None:
        err = BrickNotFoundError("missing_brick")
        assert isinstance(err, BrickError), f"Expected BrickError, got {type(err).__name__}"

    def test_message_contains_name(self) -> None:
        err = BrickNotFoundError("missing_brick")
        assert "missing_brick" in str(err), f"Expected 'missing_brick' in {str(err)!r}"

    def test_name_attribute(self) -> None:
        err = BrickNotFoundError("missing_brick")
        assert err.name == "missing_brick", f"Expected 'missing_brick', got {err.name!r}"

    def test_is_catchable_as_brick_error(self) -> None:
        with pytest.raises(BrickError):
            raise BrickNotFoundError("some_brick")


class TestBlueprintValidationError:
    def test_inherits_brick_error(self) -> None:
        err = BlueprintValidationError("invalid")
        assert isinstance(err, BrickError), f"Expected BrickError, got {type(err).__name__}"

    def test_message(self) -> None:
        err = BlueprintValidationError("bad blueprint")
        assert "bad blueprint" in str(err), f"Expected 'bad blueprint' in {str(err)!r}"

    def test_errors_list(self) -> None:
        err = BlueprintValidationError("2 errors", errors=["err1", "err2"])
        assert err.errors == ["err1", "err2"], f"Expected ['err1', 'err2'], got {err.errors!r}"

    def test_errors_default_empty_list(self) -> None:
        # Implementation returns [] (not None) when no errors list is provided
        err = BlueprintValidationError("no errors list")
        assert err.errors == [], f"Expected [], got {err.errors!r}"

    def test_errors_none_becomes_empty_list(self) -> None:
        err = BlueprintValidationError("msg", errors=None)
        assert err.errors == [], f"Expected [], got {err.errors!r}"

    def test_multiple_errors_preserved(self) -> None:
        errors = ["error 1", "error 2", "error 3"]
        err = BlueprintValidationError("3 errors", errors=errors)
        assert len(err.errors) == 3, f"Expected length 3, got {len(err.errors)}"
        assert "error 1" in err.errors, "Expected 'error 1' to be in collection"


class TestVariableResolutionError:
    def test_inherits_brick_error(self) -> None:
        err = VariableResolutionError("${unknown}")
        assert isinstance(err, BrickError), f"Expected BrickError, got {type(err).__name__}"

    def test_message_contains_reference(self) -> None:
        err = VariableResolutionError("${inputs.missing}")
        assert "inputs.missing" in str(err), f"Expected 'inputs.missing' in {str(err)!r}"

    def test_reference_attribute(self) -> None:
        err = VariableResolutionError("${my_var}")
        assert err.reference == "${my_var}", f"Expected '${{my_var}}', got {err.reference!r}"

    def test_is_catchable_as_brick_error(self) -> None:
        with pytest.raises(BrickError):
            raise VariableResolutionError("${x}")


class TestBrickExecutionError:
    def test_inherits_brick_error(self) -> None:
        err = BrickExecutionError("my_brick", "step_1", ValueError("oops"))
        assert isinstance(err, BrickError), f"Expected BrickError, got {type(err).__name__}"

    def test_message_contains_brick_and_step(self) -> None:
        err = BrickExecutionError("my_brick", "step_1", ValueError("oops"))
        msg = str(err)
        assert "my_brick" in msg, f"Expected 'my_brick' in {msg!r}"
        assert "step_1" in msg, f"Expected 'step_1' in {msg!r}"

    def test_cause_attribute(self) -> None:
        cause = ValueError("root cause")
        err = BrickExecutionError("b", "s", cause)
        assert err.cause is cause, "Expected cause to be the original exception"

    def test_brick_name_attribute(self) -> None:
        err = BrickExecutionError("my_brick", "step_1", RuntimeError())
        assert err.brick_name == "my_brick", f"Expected 'my_brick', got {err.brick_name!r}"

    def test_step_name_attribute(self) -> None:
        err = BrickExecutionError("my_brick", "step_1", RuntimeError())
        assert err.step_name == "step_1", f"Expected 'step_1', got {err.step_name!r}"

    def test_cause_preserved_exactly(self) -> None:
        original = RuntimeError("the original cause")
        err = BrickExecutionError("b", "s", original)
        assert err.cause is original, "Expected cause to be the original exception"
        assert str(original) in str(err), f"Expected original cause message in {str(err)!r}"


class TestYamlLoadError:
    def test_inherits_brick_error(self) -> None:
        err = YamlLoadError("/path/to/file.yaml", ValueError("bad yaml"))
        assert isinstance(err, BrickError), f"Expected BrickError, got {type(err).__name__}"

    def test_message_contains_path(self) -> None:
        err = YamlLoadError("/path/to/file.yaml", ValueError("bad yaml"))
        assert "/path/to/file.yaml" in str(err), f"Expected path in {str(err)!r}"

    def test_path_attribute(self) -> None:
        err = YamlLoadError("/some/path.yaml", ValueError("x"))
        assert err.path == "/some/path.yaml", f"Expected '/some/path.yaml', got {err.path!r}"

    def test_cause_attribute(self) -> None:
        cause = ValueError("root cause")
        err = YamlLoadError("/f.yaml", cause)
        assert err.cause is cause, "Expected cause to be the original exception"

    def test_string_source(self) -> None:
        err = YamlLoadError("<string>", ValueError("parse error"))
        assert "<string>" in str(err), f"Expected '<string>' in {str(err)!r}"
        assert err.path == "<string>", f"Expected '<string>', got {err.path!r}"


class TestConfigError:
    def test_inherits_brick_error(self) -> None:
        err = ConfigError("/path/config.yaml", ValueError("bad"))
        assert isinstance(err, BrickError), f"Expected BrickError, got {type(err).__name__}"

    def test_message_contains_path(self) -> None:
        err = ConfigError("/path/config.yaml", ValueError("bad"))
        assert "/path/config.yaml" in str(err), f"Expected path in {str(err)!r}"

    def test_path_attribute(self) -> None:
        err = ConfigError("/cfg.yaml", ValueError("x"))
        assert err.path == "/cfg.yaml", f"Expected '/cfg.yaml', got {err.path!r}"

    def test_cause_attribute(self) -> None:
        cause = ValueError("config parse error")
        err = ConfigError("/cfg.yaml", cause)
        assert err.cause is cause, "Expected cause to be the original exception"

    def test_is_catchable_as_brick_error(self) -> None:
        with pytest.raises(BrickError):
            raise ConfigError("/cfg.yaml", ValueError("oops"))
