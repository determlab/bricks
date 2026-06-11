"""Pydantic models for Brick metadata and YAML blueprint definitions."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class BrickMeta(BaseModel):
    """Metadata attached to a registered Brick."""

    name: str
    tags: list[str] = Field(default_factory=list)
    category: str = "general"
    destructive: bool = False
    idempotent: bool = True
    description: str = ""


class StepDefinition(BaseModel):
    """A single step within a blueprint definition (parsed from YAML).

    Steps of ``type="brick"`` (default) or ``type="blueprint"`` must specify
    exactly one of ``brick`` or ``blueprint``.  Steps of ``type="guard"`` must
    specify ``condition`` (a Python expression) and optionally ``message``.
    """

    name: str
    type: Literal["brick", "blueprint", "guard"] = "brick"
    brick: str | None = None
    blueprint: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    save_as: str | None = None
    condition: str | None = None
    message: str = "Guard condition not met"

    @model_validator(mode="after")
    def check_step_fields(self) -> StepDefinition:
        """Enforce field constraints per step type."""
        if self.type == "guard":
            if self.condition is None:
                raise ValueError("Guard step must specify 'condition'")
            return self
        if self.brick is None and self.blueprint is None:
            raise ValueError("Step must specify either 'brick' or 'blueprint'")
        if self.brick is not None and self.blueprint is not None:
            raise ValueError("Step cannot specify both 'brick' and 'blueprint'")
        return self


class BlueprintDefinition(BaseModel):
    """A complete blueprint definition (parsed from YAML).

    Represents the top-level structure of a blueprint YAML file.
    """

    name: str
    description: str = ""
    inputs: dict[str, Any] = Field(default_factory=dict)
    steps: list[StepDefinition] = Field(default_factory=list)
    outputs_map: dict[str, str] = Field(default_factory=dict)


class Verbosity(str, Enum):
    """Controls execution trace detail returned by BlueprintEngine.run()."""

    MINIMAL = "minimal"
    """Final outputs only — no step detail, no timing."""

    STANDARD = "standard"
    """Per-step outputs + final outputs. No timing overhead."""

    FULL = "full"
    """Per-step inputs + outputs + timing + total duration + final outputs."""


class StepResult(BaseModel):
    """Execution result captured for a single step."""

    step_name: str
    brick_name: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    """Resolved input parameters (populated in FULL verbosity only)."""

    outputs: dict[str, Any] = Field(default_factory=dict)
    """Step output dict (populated in STANDARD and FULL verbosity)."""

    duration_ms: float = 0.0
    """Wall-clock execution time in milliseconds (populated in FULL only)."""

    save_as: str | None = None


class ExecutionResult(BaseModel):
    """Structured result returned by BlueprintEngine.run().

    ``outputs`` is always present and matches what the old ``run()`` returned.
    ``steps``, ``total_duration_ms`` are populated according to ``verbosity``.
    """

    outputs: dict[str, Any] = Field(default_factory=dict)
    steps: list[StepResult] = Field(default_factory=list)
    total_duration_ms: float = 0.0
    blueprint_name: str = ""
    verbosity: Verbosity = Verbosity.MINIMAL
