"""Reference resolver: expands ${variable} references in step parameters."""

from __future__ import annotations

import re
from typing import Any

from bricks.core.constants import _REF_PATTERN
from bricks.core.context import ExecutionContext
from bricks.core.exceptions import VariableResolutionError


class ReferenceResolver:
    """Resolves ${variable} references against an ExecutionContext.

    Supports dotted paths like ``${inputs.channel}`` and
    ``${measured_voltage.value}``.
    """

    def resolve(self, value: Any, context: ExecutionContext) -> Any:
        """Resolve all ${...} references in a value.

        Args:
            value: A string, dict, list, or primitive. Strings are scanned
                for ``${...}`` patterns. Dicts and lists are resolved recursively.
            context: The execution context to resolve variables against.

        Returns:
            The value with all references replaced.

        Raises:
            VariableResolutionError: If a referenced variable cannot be found.
        """
        if isinstance(value, str):
            return self._resolve_string(value, context)
        if isinstance(value, dict):
            return {k: self.resolve(v, context) for k, v in value.items()}
        if isinstance(value, list):
            return [self.resolve(item, context) for item in value]
        return value

    def _resolve_string(self, text: str, context: ExecutionContext) -> Any:
        """Resolve a single string value.

        If the entire string is a single reference (e.g., ``${inputs.channel}``),
        return the resolved value directly (preserving its type).
        If the string contains embedded references mixed with text,
        substitute them as strings.
        """
        match = _REF_PATTERN.fullmatch(text)
        if match:
            return self._lookup(match.group(1), context)

        def replacer(m: re.Match[str]) -> str:
            return str(self._lookup(m.group(1), context))

        return _REF_PATTERN.sub(replacer, text)

    def _lookup(self, path: str, context: ExecutionContext) -> Any:
        """Resolve a dotted path against the context."""
        parts = path.split(".")
        try:
            current: Any = context.get_variable(parts[0])
            for part in parts[1:]:
                current = current[part] if isinstance(current, dict) else getattr(current, part)
            return current
        except (KeyError, AttributeError) as exc:
            raise VariableResolutionError(f"${{{path}}}") from exc
