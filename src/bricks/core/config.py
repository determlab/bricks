"""Project-level configuration loader for the Bricks framework."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from bricks.core.exceptions import ConfigError


class RegistryConfig(BaseModel):
    """Registry discovery configuration."""

    auto_discover: bool = False
    paths: list[str] = Field(default_factory=list)


class BlueprintsConfig(BaseModel):
    """Blueprints directory configuration."""

    base_dir: str = "blueprints/"


class AiConfig(BaseModel):
    """AI composition configuration."""

    model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 4096


class CatalogConfig(BaseModel):
    """Tiered catalog configuration.

    ``common_set`` lists brick names that are always shown by
    :meth:`~bricks.core.catalog.TieredCatalog.list_bricks` (Tier 1).
    """

    common_set: list[str] = Field(default_factory=list)


class StoreConfig(BaseModel):
    """Blueprint store configuration.

    Attributes:
        enabled: Whether the store is active. Off by default.
        backend: Storage backend — ``"memory"`` (session-scoped) or ``"file"`` (persistent).
        path: Directory path for the file backend.
        ttl_days: Number of days before an unused blueprint is considered stale.
    """

    enabled: bool = False
    backend: str = "memory"
    path: str = "blueprints/"
    ttl_days: int = 30


class SelectorConfig(BaseModel):
    """Brick selector configuration.

    Attributes:
        max_results: Maximum number of bricks returned by the selector.
        embedding_provider: Dotted path to an ``EmbeddingProvider`` class.
            Empty string disables Tier 2 (embedding) — Tier 1 keyword
            matching only.
    """

    max_results: int = 20
    embedding_provider: str = ""


class BricksConfig(BaseModel):
    """Top-level Bricks project configuration.

    Loaded from ``bricks.config.yaml`` in the project root.
    """

    version: str = "1"
    registry: RegistryConfig = Field(default_factory=RegistryConfig)
    sequences: BlueprintsConfig = Field(default_factory=BlueprintsConfig)
    ai: AiConfig = Field(default_factory=AiConfig)
    catalog: CatalogConfig = Field(default_factory=CatalogConfig)
    store: StoreConfig = Field(default_factory=StoreConfig)
    selector: SelectorConfig = Field(default_factory=SelectorConfig)


class ConfigLoader:
    """Loads BricksConfig from a YAML file or string.

    Looks for ``bricks.config.yaml`` in the given directory (default: cwd).
    Returns a default config if no file is found.
    """

    DEFAULT_FILENAME = "bricks.config.yaml"

    def __init__(self) -> None:
        """Initialise the loader with a ruamel.yaml parser."""
        self._yaml = YAML()
        self._yaml.preserve_quotes = True

    def load(self, directory: Path | None = None) -> BricksConfig:
        """Load config from a directory.

        Searches for ``bricks.config.yaml`` in *directory*.
        Returns a default ``BricksConfig`` if the file is not found.

        Args:
            directory: Directory to search. Defaults to current working directory.

        Returns:
            A validated BricksConfig.

        Raises:
            ConfigError: If the file exists but cannot be parsed.
        """
        search_dir = directory or Path.cwd()
        config_path = search_dir / self.DEFAULT_FILENAME
        if not config_path.exists():
            return BricksConfig()
        return self.load_file(config_path)

    def load_file(self, path: str | Path) -> BricksConfig:
        """Load config from a specific YAML file path.

        Args:
            path: Path to the config file (str or :class:`~pathlib.Path`).

        Returns:
            A validated BricksConfig.

        Raises:
            ConfigError: If the file cannot be parsed or fails validation.
            FileNotFoundError: If the path does not exist.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        try:
            with path.open(encoding="utf-8") as f:
                data = self._yaml.load(f)
        except YAMLError as exc:
            raise ConfigError(str(path), exc) from exc
        return self._parse(data, str(path))

    def load_string(self, content: str) -> BricksConfig:
        """Load config from a YAML string.

        Args:
            content: YAML content as a string.

        Returns:
            A validated BricksConfig.

        Raises:
            ConfigError: If the content cannot be parsed.
        """
        try:
            data = self._yaml.load(io.StringIO(content))
        except YAMLError as exc:
            raise ConfigError("<string>", exc) from exc
        return self._parse(data, "<string>")

    def _parse(self, data: Any, source: str) -> BricksConfig:
        """Parse raw YAML data into a BricksConfig.

        Args:
            data: Raw parsed YAML value (None or dict).
            source: Label for error messages.

        Returns:
            A validated BricksConfig.

        Raises:
            ConfigError: If data is invalid.
        """
        if data is None:
            return BricksConfig()
        if not isinstance(data, dict):
            raise ConfigError(source, TypeError(f"Expected mapping, got {type(data).__name__}"))
        try:
            return BricksConfig.model_validate(data)
        except ValidationError as exc:
            raise ConfigError(source, exc) from exc
