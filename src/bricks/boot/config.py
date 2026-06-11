"""SystemConfig — resolved boot configuration passed to runtime components."""

from __future__ import annotations

from pydantic import BaseModel, Field

from bricks.core.config import StoreConfig


class SystemConfig(BaseModel):
    """Resolved configuration for a Bricks runtime system.

    Produced by ``SystemBootstrapper.bootstrap()`` and consumed by
    ``RuntimeOrchestrator``. All fields have safe defaults so the config
    can be constructed programmatically without a file.

    Attributes:
        name: Human-readable system name.
        description: Free-text description of the agent's domain.
        brick_categories: Brick categories to prefer in selection.
            Empty list means all categories are considered equally.
        tags: Brick tags to prefer in selection.
        model: Claude model ID used for composition.
        api_key: Anthropic API key (empty means caller must inject).
        store: Blueprint store configuration.
        max_selector_results: Upper limit for brick selector output.
    """

    name: str
    description: str = ""
    brick_categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    model: str = "claude-haiku-4-5-20251001"
    api_key: str = ""
    store: StoreConfig = Field(default_factory=StoreConfig)
    max_selector_results: int = 20
