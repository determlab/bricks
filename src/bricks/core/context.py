"""ExecutionContext: runtime state passed through a sequence execution."""

from __future__ import annotations

from typing import Any


class ExecutionContext:
    """Mutable context that accumulates state during sequence execution.

    Stores input parameters, step results (via save_as), and provides
    variable resolution data for the reference resolver.
    """

    def __init__(self, inputs: dict[str, Any] | None = None) -> None:
        self._inputs: dict[str, Any] = inputs or {}
        self._results: dict[str, Any] = {}
        self._step_index: int = 0

    @property
    def inputs(self) -> dict[str, Any]:
        """The sequence-level input parameters."""
        return self._inputs

    @property
    def results(self) -> dict[str, Any]:
        """All saved step results (keyed by save_as names)."""
        return self._results

    @property
    def step_index(self) -> int:
        """The current step index (zero-based)."""
        return self._step_index

    def save_result(self, key: str, value: Any) -> None:
        """Store a step result for later reference.

        Args:
            key: The save_as name from the step definition.
            value: The result value to store.
        """
        self._results[key] = value

    def advance_step(self) -> None:
        """Increment the step index."""
        self._step_index += 1

    def get_variable(self, name: str) -> Any:
        """Look up a variable by name.

        Checks in order: special namespace ``inputs``, then saved results,
        then individual input keys.

        Args:
            name: Variable name to resolve.

        Returns:
            The variable value.

        Raises:
            KeyError: If *name* is not found.
        """
        if name == "inputs":
            return self._inputs
        if name in self._results:
            return self._results[name]
        if name in self._inputs:
            return self._inputs[name]
        raise KeyError(name)
