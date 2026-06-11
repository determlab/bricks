"""Dry-run validation: validates a blueprint without executing bricks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bricks.core.constants import _REF_PATTERN
from bricks.core.exceptions import BlueprintValidationError
from bricks.core.models import BlueprintDefinition
from bricks.core.registry import BrickRegistry


def _extract_references(value: Any) -> list[str]:
    """Recursively extract all ${...} reference strings from a value.

    Args:
        value: A string, dict, list, or primitive to scan.

    Returns:
        A list of raw reference strings (contents of ${...}).
    """
    refs: list[str] = []
    if isinstance(value, str):
        refs.extend(_REF_PATTERN.findall(value))
    elif isinstance(value, dict):
        for v in value.values():
            refs.extend(_extract_references(v))
    elif isinstance(value, list):
        for item in value:
            refs.extend(_extract_references(item))
    return refs


class BlueprintValidator:
    """Validates a BlueprintDefinition against the registry without executing.

    Checks:
    - All referenced bricks exist in the registry (brick steps only).
    - Sub-blueprint file paths exist on disk (blueprint steps only).
    - save_as names are unique across steps.
    - Duplicate step names are not allowed.
    - outputs_map references exist (as save_as names or input names).
    - ${inputs.X} references point to declared input names.
    - ${name} result references are not forward references or undefined.
    - Blueprint has at least one step.
    """

    def __init__(self, registry: BrickRegistry) -> None:
        """Initialise the validator.

        Args:
            registry: The brick registry to validate brick names against.
        """
        self._registry = registry

    def validate(self, blueprint: BlueprintDefinition) -> None:
        """Validate a blueprint definition and return a list of errors.

        Args:
            blueprint: The blueprint definition to validate.

        Returns:
            None. Raises BlueprintValidationError on any error.

        Raises:
            BlueprintValidationError: If the blueprint has validation errors.
        """
        errors: list[str] = []

        # Check 7: Empty blueprint guard
        if not blueprint.steps:
            errors.append(f"Blueprint {blueprint.name!r} has no steps")
            raise BlueprintValidationError(
                f"Blueprint {blueprint.name!r} has {len(errors)} validation error(s)",
                errors=errors,
            )

        # Check 1: All referenced bricks exist (brick steps) / sub-blueprint files exist (blueprint steps)
        for step in blueprint.steps:
            if step.brick is not None:
                if not self._registry.has(step.brick):
                    errors.append(f"Step {step.name!r}: brick {step.brick!r} not found in registry")
            else:
                # step.blueprint is not None here (guaranteed by model validator)
                if not Path(step.blueprint or "").exists():
                    errors.append(f"Step {step.name!r}: blueprint file {step.blueprint!r} not found")

        # Check 2: save_as uniqueness
        save_names: list[str] = []
        for step in blueprint.steps:
            if step.save_as is not None:
                if step.save_as in save_names:
                    errors.append(f"Step {step.name!r}: duplicate save_as name {step.save_as!r}")
                save_names.append(step.save_as)

        # Check 3: Duplicate step names
        step_names: list[str] = []
        for step in blueprint.steps:
            if step.name in step_names:
                errors.append(f"Duplicate step name: {step.name!r}")
            step_names.append(step.name)

        # Check 4: outputs_map reference validation
        available_names = set(save_names) | set(blueprint.inputs.keys())
        for key, ref in blueprint.outputs_map.items():
            refs = _extract_references(ref)
            for r in refs:
                if r.startswith("inputs."):
                    input_key = r[len("inputs.") :]
                    if input_key not in blueprint.inputs:
                        errors.append(f"outputs_map key {key!r}: input {input_key!r} not declared")
                else:
                    base = r.split(".")[0]
                    if base not in available_names:
                        errors.append(f"outputs_map key {key!r}: reference {r!r} not found")

        # Check 5: ${inputs.X} references in step params
        declared_inputs = set(blueprint.inputs.keys())
        for step in blueprint.steps:
            for ref in _extract_references(step.params):
                if ref.startswith("inputs."):
                    input_key = ref[len("inputs.") :]
                    if input_key not in declared_inputs:
                        errors.append(f"Step {step.name!r}: input {input_key!r} not declared")

        # Check 6: Result reference completeness (no forward references or undefined)
        prior_save_as: set[str] = set()
        all_save_as = set(save_names)
        for step in blueprint.steps:
            for ref in _extract_references(step.params):
                if ref.startswith("inputs."):
                    continue  # already checked in Check 5
                base = ref.split(".")[0]
                if base in prior_save_as:
                    continue  # valid backward reference
                if base in blueprint.inputs:
                    continue  # valid input reference
                if base in all_save_as:
                    errors.append(f"Step {step.name!r}: reference {ref!r} is not yet available")
                else:
                    errors.append(f"Step {step.name!r}: undefined variable {ref!r}")
            if step.save_as is not None:
                prior_save_as.add(step.save_as)

        if errors:
            raise BlueprintValidationError(
                f"Blueprint {blueprint.name!r} has {len(errors)} validation error(s)",
                errors=errors,
            )
