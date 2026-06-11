"""Deprecated aliases for renamed classes and functions.

These aliases existed when the engine used "Sequence" terminology.
Import from ``bricks.core`` directly instead. All aliases will be
removed in v1.0.0.
"""

from __future__ import annotations

import warnings

from bricks.core.config import BlueprintsConfig
from bricks.core.exceptions import BlueprintValidationError
from bricks.core.loader import BlueprintLoader
from bricks.core.models import BlueprintDefinition
from bricks.core.schema import blueprint_schema
from bricks.core.utils import blueprint_to_yaml
from bricks.core.validation import BlueprintValidator

_MSG = "{old!r} is deprecated, use {new!r} instead. Will be removed in v1.0.0."


def __getattr__(name: str) -> object:
    """Emit deprecation warnings on access to old Sequence* names.

    Args:
        name: The attribute name being accessed.

    Returns:
        The corresponding new class/function.

    Raises:
        AttributeError: If the name is not a known deprecated alias.
    """
    _aliases: dict[str, tuple[object, str]] = {
        "SequenceDefinition": (BlueprintDefinition, "BlueprintDefinition"),
        "SequenceEngine": (BlueprintValidator, "BlueprintEngine"),
        "SequenceLoader": (BlueprintLoader, "BlueprintLoader"),
        "SequenceValidator": (BlueprintValidator, "BlueprintValidator"),
        "SequenceValidationError": (BlueprintValidationError, "BlueprintValidationError"),
        "SequencesConfig": (BlueprintsConfig, "BlueprintsConfig"),
        "sequence_schema": (blueprint_schema, "blueprint_schema"),
        "sequence_to_yaml": (blueprint_to_yaml, "blueprint_to_yaml"),
    }
    if name in _aliases:
        obj, new_name = _aliases[name]
        warnings.warn(
            _MSG.format(old=name, new=new_name),
            DeprecationWarning,
            stacklevel=2,
        )
        return obj
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
