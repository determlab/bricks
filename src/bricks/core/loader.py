"""YAML blueprint loader: parses .yaml files into BlueprintDefinition models."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from bricks.core.exceptions import YamlLoadError
from bricks.core.models import BlueprintDefinition


def _to_plain(obj: Any) -> Any:
    """Recursively convert ruamel.yaml CommentedMap/Seq to plain Python types.

    ruamel.yaml returns ``CommentedMap`` (a dict subclass) and ``CommentedSeq``
    (a list subclass) to preserve YAML comments and key ordering.  They behave
    like built-ins in most situations but confuse ``isinstance`` checks and type
    annotations inside bricks (e.g. a brick expecting ``str`` receives a
    ``CommentedMap`` instead).  Converting before Pydantic validation ensures
    every downstream consumer only sees plain Python types.

    Args:
        obj: Any Python object, possibly containing ``CommentedMap`` /
            ``CommentedSeq`` nodes from ruamel.yaml parsing.

    Returns:
        The same structure expressed with plain :class:`dict` and :class:`list`.
    """
    if isinstance(obj, dict):
        return {k: _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_plain(item) for item in obj]
    return obj


class BlueprintLoader:
    """Loads YAML files and parses them into BlueprintDefinition instances."""

    def __init__(self) -> None:
        self._yaml = YAML()
        self._yaml.preserve_quotes = True

    def load_file(self, path: str | Path) -> BlueprintDefinition:
        """Load a BlueprintDefinition from a YAML file path.

        Args:
            path: Path to the .yaml file (str or :class:`~pathlib.Path`).

        Returns:
            A validated BlueprintDefinition.

        Raises:
            YamlLoadError: If the file cannot be parsed or does not conform to schema.
            FileNotFoundError: If the path does not exist.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Blueprint file not found: {path}")
        try:
            with path.open(encoding="utf-8") as f:
                data = self._yaml.load(f)
        except YAMLError as exc:
            raise YamlLoadError(str(path), exc) from exc
        if data is None:
            raise YamlLoadError(str(path), ValueError("Empty YAML file"))
        return self._parse_raw(data, str(path))

    def load_string(self, content: str) -> BlueprintDefinition:
        """Load a BlueprintDefinition from a YAML string.

        Args:
            content: YAML content as a string.

        Returns:
            A validated BlueprintDefinition.

        Raises:
            YamlLoadError: If the content cannot be parsed.
        """
        try:
            data = self._yaml.load(io.StringIO(content))
        except YAMLError as exc:
            raise YamlLoadError("<string>", exc) from exc
        if data is None:
            raise YamlLoadError("<string>", ValueError("Empty YAML content"))
        return self._parse_raw(data, "<string>")

    def _parse_raw(self, data: Any, source: str) -> BlueprintDefinition:
        """Convert raw YAML dict into a validated BlueprintDefinition.

        Args:
            data: Raw parsed YAML value (expected to be a dict).
            source: String label for the source (file path or '<string>'), used in
                error messages.

        Returns:
            A validated BlueprintDefinition.

        Raises:
            YamlLoadError: If data is not a mapping or fails Pydantic validation.
        """
        if not isinstance(data, dict):
            raise YamlLoadError(source, TypeError(f"Expected mapping, got {type(data).__name__}"))
        try:
            return BlueprintDefinition.model_validate(_to_plain(data))
        except ValidationError as exc:
            raise YamlLoadError(source, exc) from exc
