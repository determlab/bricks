"""Public-facing error hierarchy for the Bricks API.

These errors are raised by :class:`~bricks.api.Bricks` and its components
when something goes wrong that the *caller* should handle.  They are distinct
from the internal ``BrickError`` family in :mod:`bricks.core.exceptions`.

Usage::

    from bricks.errors import BricksConfigError

    try:
        engine = Bricks.default()
        result = engine.execute("task")
    except BricksConfigError as exc:
        print(f"Configuration problem: {exc}")
    except BricksError as exc:
        print(f"Bricks error: {exc}")
"""

from __future__ import annotations


class BricksError(Exception):
    """Base class for all public-facing Bricks errors."""


class BricksConfigError(BricksError):
    """Raised for configuration problems: missing API key, unsupported model, invalid config."""


class BricksComposeError(BricksError):
    """Raised when the LLM fails to produce a valid blueprint after all retries."""


class BricksExecutionError(BricksError):
    """Raised when a brick raises an exception at runtime.

    Attributes:
        brick: The brick name that failed.
        step: The step name in the blueprint.
        cause: The original exception.
    """

    def __init__(self, message: str, brick: str, step: str, cause: Exception) -> None:
        """Initialise the error.

        Args:
            message: Human-readable description.
            brick: Name of the failing brick.
            step: Name of the failing step.
            cause: Original exception that was raised.
        """
        super().__init__(message)
        self.brick = brick
        self.step = step
        self.cause = cause


class BricksInputError(BricksError):
    """Raised when user-supplied inputs cannot be mapped to blueprint variables."""
