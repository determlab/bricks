"""Shared utility functions for the Bricks framework."""

from __future__ import annotations

import io
import re
from typing import Any

from ruamel.yaml import YAML


def strip_code_fence(text: str) -> str:
    """Remove a markdown code fence and return the inner content.

    Handles ```python ... ```, ```yaml ... ```, and plain ``` ... ``` blocks.
    Falls back to the stripped full text if no code fence is found.

    Args:
        text: Raw text that may contain a fenced code block.

    Returns:
        The content inside the code fence, or the stripped text if none found.
    """
    match = re.search(r"```(?:\w+)?\s*\n(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def blueprint_to_yaml(sequence: Any) -> str:
    """Serialise a BlueprintDefinition to a YAML string.

    Args:
        sequence: A BlueprintDefinition instance.

    Returns:
        YAML representation of the blueprint as a string.
    """
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False

    data = {
        "name": sequence.name,
        "description": sequence.description,
        "inputs": sequence.inputs,
        "steps": [
            {
                "name": step.name,
                "brick": step.brick,
                "params": step.params,
                **({"save_as": step.save_as} if step.save_as else {}),
            }
            for step in sequence.steps
        ],
        "outputs_map": sequence.outputs_map,
    }

    stream = io.StringIO()
    yaml.dump(data, stream)
    return stream.getvalue()


# Deprecated alias — will be removed in v1.0.0
sequence_to_yaml = blueprint_to_yaml
