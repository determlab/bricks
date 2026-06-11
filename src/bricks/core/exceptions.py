"""Custom exceptions for the Bricks engine."""

from __future__ import annotations


class BrickError(Exception):
    """Base exception for all Bricks errors."""


class DuplicateBrickError(BrickError):
    """Raised when a brick name is registered more than once."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Brick already registered: {name!r}")


class DuplicateBlueprintError(BrickError):
    """Raised when a blueprint name is already in the store."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Blueprint {name!r} already exists. Delete it first to replace.")


class BrickNotFoundError(BrickError):
    """Raised when a brick name cannot be found in the registry."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Brick not found: {name!r}")


class BlueprintValidationError(BrickError):
    """Raised when a blueprint definition fails validation."""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        self.errors = errors or []
        super().__init__(message)


class VariableResolutionError(BrickError):
    """Raised when a ${variable} reference cannot be resolved."""

    def __init__(self, reference: str) -> None:
        self.reference = reference
        super().__init__(f"Cannot resolve reference: {reference!r}")


class BrickExecutionError(BrickError):
    """Raised when a brick fails during execution."""

    def __init__(self, brick_name: str, step_name: str, cause: Exception) -> None:
        self.brick_name = brick_name
        self.step_name = step_name
        self.cause = cause
        super().__init__(f"Brick {brick_name!r} failed at step {step_name!r}: {cause}")


class YamlLoadError(BrickError):
    """Raised when a YAML file cannot be parsed or loaded."""

    def __init__(self, path: str, cause: Exception) -> None:
        self.path = path
        self.cause = cause
        super().__init__(f"Failed to load YAML from {path!r}: {cause}")


class GuardFailedError(BrickError):
    """Raised when a guard step condition evaluates to False."""

    def __init__(
        self,
        step_name: str,
        condition: str,
        message: str,
        actual: str,
    ) -> None:
        self.step_name = step_name
        self.condition = condition
        self.actual = actual
        super().__init__(f"Guard {step_name!r} failed: {message}\n  Condition : {condition!r}\n  Actual    : {actual}")


class OrchestratorError(BrickError):
    """Raised when RuntimeOrchestrator.execute() cannot complete a task."""


class ConfigError(BrickError):
    """Raised when bricks.config.yaml cannot be loaded or is invalid."""

    def __init__(self, path: str, cause: Exception) -> None:
        """Initialise the error.

        Args:
            path: The config file path or '<string>' for string sources.
            cause: The underlying exception.
        """
        super().__init__(f"Config error in {path!r}: {cause}")
        self.path = path
        self.cause = cause
