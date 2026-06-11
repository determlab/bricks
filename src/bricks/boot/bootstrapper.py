"""SystemBootstrapper: reads agent.yaml, returns SystemConfig.

``agent.yaml`` → parse directly, zero LLM calls.

Free-text ``skill.md`` bootstrapping needs an LLM to extract categories and
tags, so it lives in the AI layer — see ``bricks_ai.skill_boot``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from bricks.boot.config import SystemConfig
from bricks.core.config import StoreConfig

_DEFAULT_MODEL = "claude-haiku-4-5-20251001"


class SystemBootstrapper:
    """Reads an ``agent.yaml`` config file and returns a resolved ``SystemConfig``.

    The structured YAML is parsed directly without any LLM call. Markdown
    skill descriptions (``skill.md``) are not supported here — they require
    an LLM extraction call and are handled by
    ``bricks_ai.skill_boot.bootstrap_from_skill``.
    """

    def __init__(
        self,
        api_key: str = "",
        model: str = _DEFAULT_MODEL,
    ) -> None:
        """Initialise the bootstrapper.

        Args:
            api_key: Default API key recorded in the resolved config when the
                YAML does not specify one. The engine never uses it; it is
                inert configuration consumed by the AI layer.
            model: Default model ID recorded in the resolved config.
        """
        self._api_key = api_key
        self._model = model
        self._yaml = YAML()
        self._yaml.preserve_quotes = True

    def bootstrap(self, config_path: Path) -> SystemConfig:
        """Read a config file and return a resolved ``SystemConfig``.

        Args:
            config_path: Path to ``agent.yaml``.

        Returns:
            A populated ``SystemConfig``.

        Raises:
            FileNotFoundError: If ``config_path`` does not exist.
            ValueError: If the file extension is not ``.yaml``/``.yml``.
                Markdown files get a pointer to ``bricks_ai.skill_boot``.
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        suffix = config_path.suffix.lower()
        if suffix in {".yaml", ".yml"}:
            return self._from_yaml(config_path)
        if suffix == ".md":
            raise ValueError(
                "Markdown skill configs require the AI layer: use "
                "bricks_ai.skill_boot.bootstrap_from_skill() "
                '(pip install "bricks-ai[ai]").'
            )
        raise ValueError(f"Unsupported config format {suffix!r}. Use '.yaml'.")

    # ── private helpers ────────────────────────────────────────────────────

    def _from_yaml(self, path: Path) -> SystemConfig:
        """Parse an ``agent.yaml`` file into a ``SystemConfig``.

        Args:
            path: Path to the YAML config file.

        Returns:
            A validated ``SystemConfig``.

        Raises:
            ValueError: If the YAML is malformed or missing required fields.
        """
        try:
            data: Any = self._yaml.load(path.read_text(encoding="utf-8"))
        except YAMLError as exc:
            raise ValueError(f"YAML parse error in {path}: {exc}") from exc

        if not isinstance(data, dict):
            raise ValueError(f"Expected YAML mapping in {path}, got {type(data).__name__}")

        store_raw = data.get("store", {})
        store_cfg = StoreConfig.model_validate(store_raw) if store_raw else StoreConfig()

        return SystemConfig(
            name=data.get("name", path.stem),
            description=data.get("description", ""),
            brick_categories=data.get("brick_categories", []),
            tags=data.get("tags", []),
            model=data.get("model", _DEFAULT_MODEL),
            api_key=data.get("api_key", self._api_key),
            store=store_cfg,
            max_selector_results=data.get("max_selector_results", 20),
        )
