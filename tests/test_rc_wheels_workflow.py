from pathlib import Path

from ruamel.yaml import YAML

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "rc-wheels.yml"
_yaml = YAML(typ="safe")


def _load():
    with WORKFLOW.open("r", encoding="utf-8") as f:
        return _yaml.load(f)


def test_triggers_are_push_to_main_and_workflow_dispatch():
    config = _load()
    # ruamel's "safe" loader, like PyYAML, parses the bare `on:` key as `True`.
    on = config[True] if True in config else config["on"]
    assert on["push"]["branches"] == ["main"]
    assert "workflow_dispatch" in on


def test_permissions_are_contents_read_only():
    config = _load()
    assert config["permissions"] == {"contents": "read"}


def test_uploads_artifacts():
    text = WORKFLOW.read_text("utf-8")
    assert "actions/upload-artifact" in text


def test_never_publishes():
    text = WORKFLOW.read_text("utf-8")
    for forbidden in ("twine upload", "pypi-publish", "id-token"):
        assert forbidden not in text


def test_version_carries_an_rc_local_segment():
    # CTO review: the built version must never collide with a real PyPI
    # release, so it always carries a PEP 440 local segment.
    text = WORKFLOW.read_text("utf-8")
    assert "+rc." in text


def test_manifest_has_repo_filename_and_sha256():
    text = WORKFLOW.read_text("utf-8")
    for field in ('"repo"', '"filename"', '"sha256"'):
        assert field in text


def test_asserts_exactly_one_wheel():
    text = WORKFLOW.read_text("utf-8")
    assert "exactly one" in text
