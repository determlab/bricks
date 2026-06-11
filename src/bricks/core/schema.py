"""JSON Schema generation for BrickMeta and BlueprintDefinition."""

from __future__ import annotations

import inspect
import re
import typing
from typing import TYPE_CHECKING, Any

from bricks.core.models import BlueprintDefinition
from bricks.core.registry import BrickRegistry

if TYPE_CHECKING:
    from bricks.core.catalog import TieredCatalog


def brick_schema(name: str, registry: BrickRegistry) -> dict[str, Any]:
    """Generate a JSON Schema dict describing a registered brick.

    Args:
        name: The registered brick name.
        registry: The registry to look up the brick.

    Returns:
        A JSON Schema compatible dict with brick metadata and parameter info.

    Raises:
        BrickNotFoundError: If the brick name is not registered.
    """
    callable_, meta = registry.get(name)
    params = _callable_params(callable_)
    input_keys = list(params.keys())
    out_keys = output_keys(callable_)
    schema: dict[str, Any] = {
        "name": meta.name,
        "description": meta.description,
        "tags": meta.tags,
        "category": meta.category,
        "input_keys": input_keys,
        "output_keys": out_keys,
        "destructive": meta.destructive,
        "idempotent": meta.idempotent,
        "parameters": params,
    }
    return schema


def blueprint_schema(blueprint: BlueprintDefinition) -> dict[str, Any]:
    """Generate a JSON Schema dict describing a BlueprintDefinition.

    Args:
        blueprint: The blueprint definition to describe.

    Returns:
        A JSON Schema compatible dict describing the blueprint inputs and outputs.
    """
    return {
        "name": blueprint.name,
        "description": blueprint.description,
        "inputs": blueprint.inputs,
        "steps": [
            {
                "name": step.name,
                "brick": step.brick,
                "blueprint": step.blueprint,
                "params": step.params,
                "save_as": step.save_as,
            }
            for step in blueprint.steps
        ],
        "outputs_map": blueprint.outputs_map,
    }


def registry_schema(registry: BrickRegistry) -> list[dict[str, Any]]:
    """Generate a JSON Schema list describing all registered bricks.

    Args:
        registry: The registry to enumerate.

    Returns:
        A list of brick schema dicts, sorted by brick name.
    """
    return [brick_schema(name, registry) for name, _meta in registry.list_all()]


def catalog_schema(catalog: TieredCatalog) -> dict[str, Any]:
    """Generate a schema dict describing a TieredCatalog's current visible bricks.

    Returns the bricks currently visible via :meth:`~TieredCatalog.list_bricks`
    (Tier 1 common set + Tier 3 session cache), intended for AI agent consumption.

    Args:
        catalog: The TieredCatalog to describe.

    Returns:
        A dict with ``"bricks"`` (list of visible brick schemas) and
        ``"hint"`` (instructions for the AI on how to discover more bricks).
    """
    return {
        "bricks": catalog.list_bricks(),
        "hint": (
            "This is your current brick view (common set + recently accessed). "
            "Use lookup_brick(query) to search by name, tag, or description. "
            "Use get_brick(name) to fetch a specific brick."
        ),
    }


def compact_brick_signatures(registry: BrickRegistry) -> str:
    """Generate compact, LLM-friendly brick signatures for system prompt injection.

    Returns a string like::

        add(a: float, b: float) → {result: float}
        multiply(a: float, b: float) → {result: float}
        round_value(value: float, decimals: int=2) → {result: float}

    This is ~50 tokens for 5 bricks vs ~500+ tokens for full JSON schemas.

    Args:
        registry: The registry to enumerate.

    Returns:
        Multi-line string with one signature per brick, sorted alphabetically.
    """
    lines: list[str] = []
    for name, _meta in sorted(registry.list_public(), key=lambda x: x[0]):
        callable_, _meta_obj = registry.get(name)
        param_str = signature_params(callable_)
        output_str = _signature_output(callable_)
        lines.append(f"{name}({param_str}) → {output_str}")
    return "\n".join(lines)


def output_key_table(registry: BrickRegistry) -> str:
    """Generate an output-key reference table for LLM system prompts.

    Maps each brick name to its output field names so the LLM knows
    exactly which keys to use in ``${step.key}`` references.

    Falls back to parsing keys from ``meta.description`` when
    ``output_keys()`` returns empty (function-based bricks with
    ``dict[str, X]`` return type).

    Args:
        registry: The registry to enumerate.

    Returns:
        Multi-line reference table, e.g.::

            Output keys (use EXACTLY in ${step.key} references):
              multiply      → result
              format_result → display
    """
    entries: list[tuple[str, str]] = []
    for name, meta in sorted(registry.list_all(), key=lambda x: x[0]):
        callable_, _ = registry.get(name)
        keys = output_keys(callable_)
        if not keys:
            keys = parse_description_keys(meta.description)
        entries.append((name, ", ".join(keys) if keys else "dict"))

    if not entries:
        return ""

    max_name = max(len(name) for name, _ in entries)
    lines = ["Output keys (use EXACTLY in ${step.key} references):"]
    for name, keys_str in entries:
        lines.append(f"  {name:<{max_name}} → {keys_str}")
    return "\n".join(lines)


def parse_description_keys(description: str) -> list[str]:
    """Extract output key names from a brick description's {key: type} pattern.

    Args:
        description: Brick description string (e.g. "Returns {result: float}").

    Returns:
        List of key names found, or empty list.
    """
    return re.findall(r"\{(\w+):", description)


def _format_annotation(ann: Any) -> str:
    """Format a type annotation for LLM-readable signature output.

    Handles ``Literal`` types specially so the LLM sees valid values
    instead of the verbose ``typing.Literal[...]`` repr.

    Args:
        ann: A type annotation (e.g. ``str``, ``Literal["sum", "avg"]``).

    Returns:
        Formatted string — e.g. ``'"sum"|"avg"'`` for Literal types,
        ``'str'`` for standard types.
    """
    origin = getattr(ann, "__origin__", None)
    if origin is typing.Literal:
        return "|".join(repr(a) for a in ann.__args__)
    if hasattr(ann, "__name__"):
        return str(ann.__name__)
    return str(ann)


def signature_params(callable_: Any) -> str:
    """Format parameter signature for a callable.

    Args:
        callable_: A Python callable.

    Returns:
        Formatted parameter string like ``a: float, b: float, decimals: int=2``.
    """
    parts: list[str] = []
    try:
        sig = inspect.signature(callable_)
        # Resolve stringified annotations (from __future__ import annotations)
        try:
            resolved_hints = typing.get_type_hints(
                callable_,
                localns=vars(typing),
                include_extras=True,
            )
        except Exception:
            resolved_hints = {}
        for pname, param in sig.parameters.items():
            if pname in ("self", "inputs", "metadata"):
                continue
            ann = resolved_hints.get(pname, param.annotation)
            type_name = _format_annotation(ann)
            if ann is inspect.Parameter.empty:
                type_name = "Any"
            if param.default is not inspect.Parameter.empty:
                try:
                    default_repr = repr(param.default)
                except Exception:
                    default_repr = str(param.default)
                parts.append(f"{pname}: {type_name}={default_repr}")
            else:
                parts.append(f"{pname}: {type_name}")
    except (ValueError, TypeError):
        pass
    return ", ".join(parts)


def _signature_output(callable_: Any) -> str:
    """Format output signature for a callable.

    Args:
        callable_: A Python callable.

    Returns:
        Formatted output string like ``{result: float}`` or ``dict``.
    """
    # Class-based brick: check for Output inner class with model_fields
    cls = callable_ if isinstance(callable_, type) else type(callable_)
    output_cls = getattr(cls, "Output", None)
    if output_cls is not None and hasattr(output_cls, "model_fields"):
        fields = []
        for field_name, field_info in output_cls.model_fields.items():
            ftype = field_info.annotation
            type_name = ftype.__name__ if hasattr(ftype, "__name__") else str(ftype)
            fields.append(f"{field_name}: {type_name}")
        return "{" + ", ".join(fields) + "}"

    # Function-based brick: inspect return annotation
    try:
        hints = inspect.get_annotations(callable_, eval_str=True)
        ret = hints.get("return")
        if ret is not None:
            origin = getattr(ret, "__origin__", None)
            if origin is dict:
                args = getattr(ret, "__args__", None)
                if args and len(args) == 2:
                    vtype = args[1]
                    type_name = vtype.__name__ if hasattr(vtype, "__name__") else str(vtype)
                    return "{...: " + type_name + "}"
    except Exception:  # noqa: S110
        pass

    return "dict"


def output_keys(callable_: Any) -> list[str]:
    """Extract output key names from a callable's return type annotation.

    Inspects the return type annotation for ``dict[str, ...]`` patterns
    and falls back to calling the function's class-based Output schema
    if available. Returns an empty list if output keys cannot be determined.

    Args:
        callable_: A Python callable (function or class instance).

    Returns:
        List of output key names.
    """
    # Class-based brick: check for Output inner class
    cls = callable_ if isinstance(callable_, type) else type(callable_)
    output_cls = getattr(cls, "Output", None)
    if output_cls is not None and hasattr(output_cls, "model_fields"):
        return list(output_cls.model_fields.keys())

    # Function-based brick: inspect return annotation for TypedDict or dict hints
    try:
        hints = inspect.get_annotations(callable_, eval_str=True)
        ret = hints.get("return")
        if ret is not None:
            origin = getattr(ret, "__origin__", None)
            if origin is dict:
                # Can't extract keys from generic dict[str, X]
                return []
    except Exception:  # noqa: S110
        pass

    return []


def _callable_params(callable_: Any) -> dict[str, Any]:
    """Extract parameter information from a callable using inspect.

    Args:
        callable_: A Python callable (function or bound method).

    Returns:
        A dict mapping parameter names to their annotation strings.
    """
    params: dict[str, Any] = {}
    try:
        sig = inspect.signature(callable_)
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "inputs", "metadata"):
                continue
            annotation = str(param.annotation) if param.annotation is not inspect.Parameter.empty else "Any"
            params[param_name] = {
                "type": annotation,
                "required": param.default is inspect.Parameter.empty,
            }
    except (ValueError, TypeError):
        pass
    return params
