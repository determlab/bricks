"""Tests for bricks.core.config."""

from __future__ import annotations

from pathlib import Path

import pytest

from bricks.core.config import BlueprintsConfig, BricksConfig, ConfigLoader
from bricks.core.exceptions import ConfigError


class TestDefaultConfig:
    def test_default_config_is_valid(self) -> None:
        config = BricksConfig()
        assert config.version == "1", f"Expected '1', got {config.version!r}"
        assert config.registry.auto_discover is False, f"Expected False, got {config.registry.auto_discover!r}"
        assert config.registry.paths == [], f"Expected [], got {config.registry.paths!r}"
        assert config.sequences.base_dir == "blueprints/", f"Expected 'blueprints/', got {config.sequences.base_dir!r}"
        assert config.ai.model == "claude-haiku-4-5-20251001", f"Expected claude model, got {config.ai.model!r}"
        assert config.ai.max_tokens == 4096, f"Expected 4096, got {config.ai.max_tokens!r}"

    def test_load_returns_default_when_no_file(self, tmp_path: Path) -> None:
        loader = ConfigLoader()
        config = loader.load(directory=tmp_path)
        assert isinstance(config, BricksConfig), f"Expected BricksConfig, got {type(config).__name__}"
        assert config.registry.auto_discover is False, f"Expected False, got {config.registry.auto_discover!r}"

    def test_blueprints_config_default(self) -> None:
        bp_config = BlueprintsConfig()
        assert bp_config.base_dir == "blueprints/", f"Expected 'blueprints/', got {bp_config.base_dir!r}"


class TestLoadString:
    def test_load_full_config(self) -> None:
        loader = ConfigLoader()
        yaml_content = """
version: "1"
registry:
  auto_discover: true
  paths:
    - "bricks_lib/"
    - "custom_bricks.py"
sequences:
  base_dir: "my_blueprints/"
ai:
  model: "claude-haiku-4-5-20251001"
  max_tokens: 2048
"""
        config = loader.load_string(yaml_content)
        assert config.version == "1", f"Expected '1', got {config.version!r}"
        assert config.registry.auto_discover is True, f"Expected True, got {config.registry.auto_discover!r}"
        assert config.registry.paths == ["bricks_lib/", "custom_bricks.py"], "Expected paths mismatch"
        assert config.sequences.base_dir == "my_blueprints/", (
            f"Expected 'my_blueprints/', got {config.sequences.base_dir!r}"
        )
        assert config.ai.model == "claude-haiku-4-5-20251001", f"Expected claude model, got {config.ai.model!r}"
        assert config.ai.max_tokens == 2048, f"Expected 2048, got {config.ai.max_tokens!r}"

    def test_load_partial_config_uses_defaults(self) -> None:
        loader = ConfigLoader()
        config = loader.load_string("registry:\n  auto_discover: true\n")
        assert config.registry.auto_discover is True, f"Expected True, got {config.registry.auto_discover!r}"
        assert config.ai.max_tokens == 4096, f"Expected 4096, got {config.ai.max_tokens!r}"

    def test_empty_yaml_returns_default(self) -> None:
        loader = ConfigLoader()
        config = loader.load_string("")
        assert isinstance(config, BricksConfig), f"Expected BricksConfig, got {type(config).__name__}"

    def test_invalid_yaml_raises_config_error(self) -> None:
        loader = ConfigLoader()
        with pytest.raises(ConfigError):
            loader.load_string("invalid: yaml: [unclosed")

    def test_wrong_type_raises_config_error(self) -> None:
        loader = ConfigLoader()
        with pytest.raises(ConfigError):
            loader.load_string("- this\n- is\n- a list\n")


class TestLoadFile:
    def test_load_file_reads_yaml(self, tmp_path: Path) -> None:
        config_file = tmp_path / "bricks.config.yaml"
        config_file.write_text("registry:\n  auto_discover: true\n  paths:\n    - 'bricks/'\n")
        loader = ConfigLoader()
        config = loader.load_file(config_file)
        assert config.registry.auto_discover is True, f"Expected True, got {config.registry.auto_discover!r}"
        assert config.registry.paths == ["bricks/"], f"Expected ['bricks/'], got {config.registry.paths!r}"

    def test_load_file_raises_for_missing_file(self, tmp_path: Path) -> None:
        loader = ConfigLoader()
        with pytest.raises(FileNotFoundError):
            loader.load_file(tmp_path / "nonexistent.yaml")

    def test_load_searches_for_default_filename(self, tmp_path: Path) -> None:
        config_file = tmp_path / "bricks.config.yaml"
        config_file.write_text("ai:\n  max_tokens: 1000\n")
        loader = ConfigLoader()
        config = loader.load(directory=tmp_path)
        assert config.ai.max_tokens == 1000, f"Expected 1000, got {config.ai.max_tokens!r}"


class TestConfigError:
    def test_config_error_message_includes_path(self) -> None:
        err = ConfigError("/path/to/config.yaml", ValueError("bad value"))
        assert "/path/to/config.yaml" in str(err), f"Expected path in {str(err)!r}"
        assert err.path == "/path/to/config.yaml", f"Expected '/path/to/config.yaml', got {err.path!r}"
