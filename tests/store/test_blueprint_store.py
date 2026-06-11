"""Tests for bricks.store — blueprint store backends and models."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from bricks.core.exceptions import DuplicateBlueprintError
from bricks.store.blueprint_store import FileBlueprintStore, MemoryBlueprintStore
from bricks.store.models import StoredBlueprint, task_fingerprint

# ── Helpers ────────────────────────────────────────────────────────────────


def _make_bp(name: str = "test_bp", fp: str = "abc123") -> StoredBlueprint:
    """Build a minimal StoredBlueprint for testing."""
    now = datetime.now(timezone.utc)
    return StoredBlueprint(
        name=name,
        yaml=f"name: {name}\nsteps: []\n",
        fingerprints=[fp],
        created_at=now,
        last_used=now,
    )


# ── task_fingerprint ────────────────────────────────────────────────────────


class TestTaskFingerprint:
    """Tests for task_fingerprint()."""

    def test_returns_64_char_hex(self) -> None:
        """Fingerprint is a 64-character lowercase hex string."""
        fp = task_fingerprint("hello")
        assert len(fp) == 64, f"Expected 64 chars, got {len(fp)}"
        assert all(c in "0123456789abcdef" for c in fp), "Not lowercase hex"

    def test_deterministic(self) -> None:
        """Same task produces same fingerprint every time."""
        task = "Calculate property valuation"
        assert task_fingerprint(task) == task_fingerprint(task)

    def test_different_tasks_differ(self) -> None:
        """Different task texts produce different fingerprints."""
        assert task_fingerprint("task A") != task_fingerprint("task B")

    def test_whitespace_sensitive(self) -> None:
        """Leading/trailing whitespace changes the fingerprint."""
        assert task_fingerprint("task") != task_fingerprint(" task")


# ── StoredBlueprint ─────────────────────────────────────────────────────────


class TestStoredBlueprint:
    """Tests for the StoredBlueprint model."""

    def test_defaults(self) -> None:
        """StoredBlueprint has sensible defaults for optional fields."""
        bp = StoredBlueprint(name="bp", yaml="name: bp\n")
        assert bp.fingerprints == [], f"Expected [], got {bp.fingerprints}"
        assert bp.use_count == 0

    def test_serialization_roundtrip(self) -> None:
        """StoredBlueprint survives JSON serialization and deserialization."""
        original = _make_bp("roundtrip", "fp1")
        restored = StoredBlueprint.model_validate_json(original.model_dump_json())
        assert restored.name == original.name
        assert restored.yaml == original.yaml
        assert restored.fingerprints == original.fingerprints
        assert restored.use_count == original.use_count


# ── MemoryBlueprintStore ────────────────────────────────────────────────────


class TestMemoryBlueprintStore:
    """Tests for MemoryBlueprintStore."""

    def test_save_and_get_by_name(self) -> None:
        """save() then get_by_name() returns the same blueprint."""
        store = MemoryBlueprintStore()
        bp = _make_bp("alpha")
        store.save(bp)
        result = store.get_by_name("alpha")
        assert result is not None
        assert result.name == "alpha"

    def test_get_by_name_missing_returns_none(self) -> None:
        """get_by_name() returns None for unknown names."""
        store = MemoryBlueprintStore()
        assert store.get_by_name("nope") is None

    def test_get_by_fingerprint(self) -> None:
        """get_by_fingerprint() finds blueprint by task hash."""
        store = MemoryBlueprintStore()
        bp = _make_bp("beta", fp="deadbeef")
        store.save(bp)
        result = store.get_by_fingerprint("deadbeef")
        assert result is not None
        assert result.name == "beta"

    def test_get_by_fingerprint_missing_returns_none(self) -> None:
        """get_by_fingerprint() returns None for unknown fingerprint."""
        store = MemoryBlueprintStore()
        assert store.get_by_fingerprint("unknown") is None

    def test_duplicate_raises(self) -> None:
        """save() raises DuplicateBlueprintError when name already exists."""
        store = MemoryBlueprintStore()
        store.save(_make_bp("dup"))
        with pytest.raises(DuplicateBlueprintError) as exc_info:
            store.save(_make_bp("dup"))
        assert "dup" in str(exc_info.value)

    def test_delete_removes_entry(self) -> None:
        """delete() removes the blueprint and its fingerprint index."""
        store = MemoryBlueprintStore()
        bp = _make_bp("gamma", fp="fp_gamma")
        store.save(bp)
        store.delete("gamma")
        assert store.get_by_name("gamma") is None
        assert store.get_by_fingerprint("fp_gamma") is None

    def test_delete_nonexistent_is_noop(self) -> None:
        """delete() on a non-existent name does not raise."""
        store = MemoryBlueprintStore()
        store.delete("phantom")  # should not raise

    def test_list_all_sorted_by_name(self) -> None:
        """list_all() returns blueprints sorted alphabetically by name."""
        store = MemoryBlueprintStore()
        store.save(_make_bp("zebra"))
        store.save(_make_bp("apple"))
        store.save(_make_bp("mango"))
        names = [bp.name for bp in store.list_all()]
        assert names == ["apple", "mango", "zebra"], f"Got {names}"

    def test_list_all_empty(self) -> None:
        """list_all() returns empty list for empty store."""
        assert MemoryBlueprintStore().list_all() == []

    def test_touch_increments_use_count(self) -> None:
        """touch() increments use_count and updates last_used."""
        store = MemoryBlueprintStore()
        bp = _make_bp("touch_me")
        store.save(bp)
        store.touch("touch_me")
        store.touch("touch_me")
        result = store.get_by_name("touch_me")
        assert result is not None
        assert result.use_count == 2, f"Expected 2, got {result.use_count}"

    def test_touch_nonexistent_is_noop(self) -> None:
        """touch() on a non-existent name does not raise."""
        MemoryBlueprintStore().touch("ghost")

    def test_purge_stale_returns_zero(self) -> None:
        """purge_stale() always returns 0 for in-memory store."""
        store = MemoryBlueprintStore()
        store.save(_make_bp("old"))
        assert store.purge_stale(0) == 0


# ── FileBlueprintStore ──────────────────────────────────────────────────────


class TestFileBlueprintStore:
    """Tests for FileBlueprintStore."""

    def test_save_creates_json_file(self, tmp_path: Path) -> None:
        """save() writes a .json file named after the blueprint."""
        store = FileBlueprintStore(tmp_path)
        store.save(_make_bp("file_bp"))
        assert (tmp_path / "file_bp.json").exists()

    def test_get_by_name_roundtrip(self, tmp_path: Path) -> None:
        """save() then get_by_name() returns the same blueprint."""
        store = FileBlueprintStore(tmp_path)
        bp = _make_bp("persist_me", fp="fp_persist")
        store.save(bp)

        store2 = FileBlueprintStore(tmp_path)
        result = store2.get_by_name("persist_me")
        assert result is not None
        assert result.name == "persist_me"
        assert "fp_persist" in result.fingerprints

    def test_get_by_fingerprint(self, tmp_path: Path) -> None:
        """get_by_fingerprint() finds blueprint on disk."""
        store = FileBlueprintStore(tmp_path)
        store.save(_make_bp("fptest", fp="fp_file"))
        assert store.get_by_fingerprint("fp_file") is not None

    def test_get_by_fingerprint_empty_dir(self, tmp_path: Path) -> None:
        """get_by_fingerprint() returns None when directory is empty."""
        assert FileBlueprintStore(tmp_path).get_by_fingerprint("nope") is None

    def test_get_by_name_missing_returns_none(self, tmp_path: Path) -> None:
        """get_by_name() returns None for non-existent blueprint."""
        assert FileBlueprintStore(tmp_path).get_by_name("missing") is None

    def test_duplicate_raises(self, tmp_path: Path) -> None:
        """save() raises DuplicateBlueprintError when JSON file already exists."""
        store = FileBlueprintStore(tmp_path)
        store.save(_make_bp("dup_file"))
        with pytest.raises(DuplicateBlueprintError):
            store.save(_make_bp("dup_file"))

    def test_delete_removes_file(self, tmp_path: Path) -> None:
        """delete() removes the blueprint JSON file."""
        store = FileBlueprintStore(tmp_path)
        store.save(_make_bp("to_delete"))
        store.delete("to_delete")
        assert not (tmp_path / "to_delete.json").exists()

    def test_list_all(self, tmp_path: Path) -> None:
        """list_all() returns all stored blueprints."""
        store = FileBlueprintStore(tmp_path)
        store.save(_make_bp("z_last"))
        store.save(_make_bp("a_first"))
        names = [bp.name for bp in store.list_all()]
        assert "a_first" in names
        assert "z_last" in names

    def test_touch_updates_use_count_on_disk(self, tmp_path: Path) -> None:
        """touch() persists use_count increment to disk."""
        store = FileBlueprintStore(tmp_path)
        store.save(_make_bp("touchable"))
        store.touch("touchable")
        result = FileBlueprintStore(tmp_path).get_by_name("touchable")
        assert result is not None
        assert result.use_count == 1

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        """Blueprint saved in one instance is readable by a new instance."""
        FileBlueprintStore(tmp_path).save(_make_bp("cross_instance"))
        result = FileBlueprintStore(tmp_path).get_by_name("cross_instance")
        assert result is not None

    def test_purge_stale_removes_old_entries(self, tmp_path: Path) -> None:
        """purge_stale() removes blueprints whose last_used exceeds TTL."""
        store = FileBlueprintStore(tmp_path)
        old_time = datetime.now(timezone.utc) - timedelta(days=40)
        bp = StoredBlueprint(
            name="stale_bp",
            yaml="name: stale_bp\n",
            fingerprints=["fp_stale"],
            created_at=old_time,
            last_used=old_time,
        )
        store.save(bp)
        store.save(_make_bp("fresh_bp"))  # recent last_used

        purged = store.purge_stale(ttl_days=30)
        assert purged == 1, f"Expected 1 purged, got {purged}"
        assert store.get_by_name("stale_bp") is None
        assert store.get_by_name("fresh_bp") is not None

    def test_purge_stale_empty_dir(self, tmp_path: Path) -> None:
        """purge_stale() returns 0 when the directory has no files."""
        assert FileBlueprintStore(tmp_path).purge_stale(30) == 0

    def test_store_dir_created_on_save(self, tmp_path: Path) -> None:
        """Store directory is created automatically on first save."""
        subdir = tmp_path / "nested" / "store"
        store = FileBlueprintStore(subdir)
        store.save(_make_bp("mkdir_test"))
        assert subdir.is_dir()
