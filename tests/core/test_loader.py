"""Tests for bricks.core.loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from bricks.core.exceptions import YamlLoadError
from bricks.core.loader import BlueprintLoader


class TestBlueprintLoaderFromString:
    def test_load_minimal_blueprint(self) -> None:
        loader = BlueprintLoader()
        bp = loader.load_string("name: test_bp\n")
        assert bp.name == "test_bp", f"Expected 'test_bp', got {bp.name!r}"
        assert bp.steps == [], f"Expected [], got {bp.steps!r}"

    def test_load_blueprint_with_steps(self) -> None:
        loader = BlueprintLoader()
        yaml = "name: my_bp\nsteps:\n  - name: s1\n    brick: do_thing\n"
        bp = loader.load_string(yaml)
        assert len(bp.steps) == 1, f"Expected length 1, got {len(bp.steps)}"
        assert bp.steps[0].name == "s1", f"Expected 's1', got {bp.steps[0].name!r}"
        assert bp.steps[0].brick == "do_thing", f"Expected 'do_thing', got {bp.steps[0].brick!r}"

    def test_load_blueprint_with_params_and_save_as(self) -> None:
        loader = BlueprintLoader()
        yaml = (
            "name: my_bp\n"
            "steps:\n"
            "  - name: s1\n"
            "    brick: read_voltage\n"
            "    params:\n"
            "      channel: 3\n"
            "    save_as: reading\n"
        )
        bp = loader.load_string(yaml)
        assert bp.steps[0].params == {"channel": 3}, f"Expected {{'channel': 3}}, got {bp.steps[0].params!r}"
        assert bp.steps[0].save_as == "reading", f"Expected 'reading', got {bp.steps[0].save_as!r}"

    def test_load_blueprint_with_inputs_and_outputs_map(self) -> None:
        loader = BlueprintLoader()
        yaml = (
            "name: my_bp\n"
            "inputs:\n"
            "  voltage: float\n"
            "steps:\n"
            "  - name: s1\n"
            "    brick: read\n"
            "    save_as: result\n"
            "outputs_map:\n"
            '  final: "${result}"\n'
        )
        bp = loader.load_string(yaml)
        assert bp.inputs == {"voltage": "float"}, f"Expected {{'voltage': 'float'}}, got {bp.inputs!r}"
        assert bp.outputs_map == {"final": "${result}"}, "Expected outputs_map mismatch"

    def test_invalid_yaml_syntax_raises(self) -> None:
        loader = BlueprintLoader()
        with pytest.raises(YamlLoadError):
            loader.load_string("name: [invalid yaml\n  missing bracket")

    def test_missing_required_name_raises(self) -> None:
        loader = BlueprintLoader()
        with pytest.raises(YamlLoadError):
            loader.load_string("description: no name field\n")

    def test_empty_content_raises(self) -> None:
        loader = BlueprintLoader()
        with pytest.raises(YamlLoadError):
            loader.load_string("")


class TestBlueprintLoaderFromFile:
    def test_load_from_yaml_file(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("name: file_test\nsteps:\n  - name: s1\n    brick: x\n")
        loader = BlueprintLoader()
        bp = loader.load_file(yaml_file)
        assert bp.name == "file_test", f"Expected 'file_test', got {bp.name!r}"

    def test_file_not_found_raises(self) -> None:
        loader = BlueprintLoader()
        with pytest.raises(FileNotFoundError):
            loader.load_file(Path("/nonexistent/file.yaml"))

    def test_empty_file_raises(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")
        loader = BlueprintLoader()
        with pytest.raises(YamlLoadError):
            loader.load_file(yaml_file)

    def test_load_file_accepts_str_path(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "str_path.yaml"
        yaml_file.write_text("name: str_test\nsteps:\n  - name: s1\n    brick: x\n")
        loader = BlueprintLoader()
        bp = loader.load_file(str(yaml_file))
        assert bp.name == "str_test"
