"""InputMapper: maps user-supplied input keys to blueprint variable names."""

from __future__ import annotations

from typing import Any

from bricks.errors import BricksInputError


class InputMapper:
    """Maps user-supplied input keys to blueprint variable names.

    Rules (applied in order):
    1. Blueprint expects 0 inputs → return user_inputs unchanged
    2. User keys already match blueprint keys → return unchanged
    3. Exactly 1 user key and 1 blueprint key → remap regardless of name
    4. len(user_inputs) == len(blueprint_inputs) → map by position
    5. Otherwise → raise BricksInputError
    """

    def map(
        self,
        user_inputs: dict[str, Any],
        blueprint_inputs: list[str],
    ) -> dict[str, Any]:
        """Map user input keys to blueprint variable names.

        Args:
            user_inputs: Dict of inputs the user provided.
            blueprint_inputs: Ordered list of variable names the blueprint expects.

        Returns:
            A new dict with keys remapped to blueprint variable names.

        Raises:
            BricksInputError: When the count mismatch cannot be auto-resolved.
        """
        # Rule 1: blueprint expects no inputs
        if not blueprint_inputs:
            return user_inputs

        user_keys = list(user_inputs.keys())
        user_vals = list(user_inputs.values())

        # Rule 2: keys already match (same set, regardless of order)
        if set(user_keys) == set(blueprint_inputs):
            return user_inputs

        # Rule 3 & 4: same count → positional mapping
        if len(user_keys) == len(blueprint_inputs):
            return dict(zip(blueprint_inputs, user_vals, strict=True))

        # Rule 5: mismatch
        raise BricksInputError(
            f"Blueprint expects {len(blueprint_inputs)} input(s) "
            f"({', '.join(blueprint_inputs)}) but got {len(user_keys)} "
            f"key(s) ({', '.join(user_keys)}). Cannot auto-map. "
            "Use matching key names or provide the same number of inputs."
        )
