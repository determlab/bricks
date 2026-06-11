"""Tests for bricks.boot — SystemBootstrapper and SystemConfig (YAML only, no LLM)."""

from __future__ import annotations

from pathlib import Path

import pytest

from bricks.boot.bootstrapper import SystemBootstrapper
from bricks.boot.config import SystemConfig

# ── Helpers ────────────────────────────────────────────────────────────────


def _write(tmp_path: Path, filename: str, content: str) -> Path:
    """Write content to a temp file and return its path."""
    p = tmp_path / filename
    p.write_text(content, encoding="utf-8")
    return p


# ── TestSystemConfig ────────────────────────────────────────────────────────


class TestSystemConfig:
    """Tests for the SystemConfig model."""

    def test_defaults(self) -> None:
        """SystemConfig has safe defaults for all optional fields."""
        cfg = SystemConfig(name="test")
        assert cfg.description == ""
        assert cfg.brick_categories == []
        assert cfg.tags == []
        assert cfg.api_key == ""
        assert cfg.max_selector_results == 20

    def test_store_default_disabled(self) -> None:
        """StoreConfig defaults to disabled."""
        cfg = SystemConfig(name="test")
        assert cfg.store.enabled is False


# ── TestBootstrapperYaml ────────────────────────────────────────────────────


class TestBootstrapperYaml:
    """Tests for YAML config bootstrapping (no LLM call)."""

    def test_yaml_parses_name(self, tmp_path: Path) -> None:
        """Bootstrap from agent.yaml returns correct name."""
        p = _write(tmp_path, "agent.yaml", "name: crm_processor\n")
        cfg = SystemBootstrapper().bootstrap(p)
        assert cfg.name == "crm_processor"

    def test_yaml_parses_all_fields(self, tmp_path: Path) -> None:
        """All fields in agent.yaml round-trip correctly."""
        yaml_content = """\
name: my_agent
description: "Processes CRM data"
brick_categories:
  - data_transformation
  - math
tags:
  - aggregation
model: claude-haiku-4-5-20251001
max_selector_results: 10
store:
  enabled: true
  backend: memory
"""
        p = _write(tmp_path, "agent.yaml", yaml_content)
        cfg = SystemBootstrapper().bootstrap(p)
        assert cfg.name == "my_agent"
        assert cfg.description == "Processes CRM data"
        assert cfg.brick_categories == ["data_transformation", "math"]
        assert cfg.tags == ["aggregation"]
        assert cfg.model == "claude-haiku-4-5-20251001"
        assert cfg.max_selector_results == 10
        assert cfg.store.enabled is True

    def test_yml_extension_supported(self, tmp_path: Path) -> None:
        """Bootstrap works with .yml extension as well as .yaml."""
        p = _write(tmp_path, "config.yml", "name: yml_test\n")
        cfg = SystemBootstrapper().bootstrap(p)
        assert cfg.name == "yml_test"

    def test_yaml_missing_name_uses_stem(self, tmp_path: Path) -> None:
        """Missing name field falls back to the file stem."""
        p = _write(tmp_path, "my_agent.yaml", "description: no name here\n")
        cfg = SystemBootstrapper().bootstrap(p)
        assert cfg.name == "my_agent"


# ── TestBootstrapperErrors ──────────────────────────────────────────────────


class TestBootstrapperErrors:
    """Tests for bootstrapper error handling."""

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """Non-existent path raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            SystemBootstrapper().bootstrap(tmp_path / "missing.yaml")

    def test_unsupported_extension_raises(self, tmp_path: Path) -> None:
        """Unsupported file extension raises ValueError."""
        p = _write(tmp_path, "config.toml", "name = 'test'\n")
        with pytest.raises(ValueError, match="Unsupported config format"):
            SystemBootstrapper().bootstrap(p)

    def test_markdown_points_to_ai_layer(self, tmp_path: Path) -> None:
        """Markdown skill configs are an AI-layer feature; the engine says so."""
        p = _write(tmp_path, "skill.md", "# Agent\nDoes things.\n")
        with pytest.raises(ValueError, match=r"bricks_ai\.skill_boot"):
            SystemBootstrapper().bootstrap(p)
