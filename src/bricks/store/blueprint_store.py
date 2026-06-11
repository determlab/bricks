"""Blueprint store backends: in-memory and file-system."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from bricks.core.exceptions import DuplicateBlueprintError
from bricks.store.models import StoredBlueprint


class BlueprintStore(ABC):
    """Abstract base class for blueprint stores.

    A store caches validated blueprints so that identical tasks can be
    served without an LLM call (zero tokens on cache hit).
    """

    @abstractmethod
    def save(self, blueprint: StoredBlueprint) -> None:
        """Persist a blueprint.

        Args:
            blueprint: The blueprint to save.

        Raises:
            DuplicateBlueprintError: If a blueprint with the same name already exists.
        """

    @abstractmethod
    def get_by_name(self, name: str) -> StoredBlueprint | None:
        """Retrieve a blueprint by name.

        Args:
            name: Blueprint name.

        Returns:
            The stored blueprint, or ``None`` if not found.
        """

    @abstractmethod
    def get_by_fingerprint(self, fingerprint: str) -> StoredBlueprint | None:
        """Retrieve a blueprint by task fingerprint.

        Args:
            fingerprint: SHA-256 hex digest of a task text.

        Returns:
            The stored blueprint, or ``None`` if not found.
        """

    @abstractmethod
    def touch(self, name: str) -> None:
        """Update ``last_used`` and increment ``use_count`` for a blueprint.

        Args:
            name: Blueprint name.
        """

    @abstractmethod
    def delete(self, name: str) -> None:
        """Remove a blueprint from the store.

        Args:
            name: Blueprint name. No-op if not found.
        """

    @abstractmethod
    def list_all(self) -> list[StoredBlueprint]:
        """Return all stored blueprints, sorted by name.

        Returns:
            List of stored blueprints.
        """

    @abstractmethod
    def purge_stale(self, ttl_days: int) -> int:
        """Delete blueprints not used within ``ttl_days`` days.

        Args:
            ttl_days: Age threshold in days.

        Returns:
            Number of blueprints purged.
        """


class MemoryBlueprintStore(BlueprintStore):
    """In-memory blueprint store — session-scoped, not persistent.

    Suitable for single-process caching. All data is lost when the process exits.
    """

    def __init__(self) -> None:
        """Initialise an empty in-memory store."""
        self._by_name: dict[str, StoredBlueprint] = {}
        self._fp_index: dict[str, str] = {}  # fingerprint → name

    def save(self, blueprint: StoredBlueprint) -> None:
        """Persist a blueprint in memory.

        Args:
            blueprint: The blueprint to save.

        Raises:
            DuplicateBlueprintError: If a blueprint with the same name already exists.
        """
        if blueprint.name in self._by_name:
            raise DuplicateBlueprintError(blueprint.name)
        self._by_name[blueprint.name] = blueprint
        for fp in blueprint.fingerprints:
            self._fp_index[fp] = blueprint.name

    def get_by_name(self, name: str) -> StoredBlueprint | None:
        """Retrieve a blueprint by name.

        Args:
            name: Blueprint name.

        Returns:
            The stored blueprint, or ``None`` if not found.
        """
        return self._by_name.get(name)

    def get_by_fingerprint(self, fingerprint: str) -> StoredBlueprint | None:
        """Retrieve a blueprint by task fingerprint.

        Args:
            fingerprint: SHA-256 hex digest of a task text.

        Returns:
            The stored blueprint, or ``None`` if not found.
        """
        name = self._fp_index.get(fingerprint)
        if name is None:
            return None
        return self._by_name.get(name)

    def touch(self, name: str) -> None:
        """Update last_used and increment use_count.

        Args:
            name: Blueprint name. No-op if not found.
        """
        bp = self._by_name.get(name)
        if bp is None:
            return
        bp.last_used = datetime.now(timezone.utc)
        bp.use_count += 1

    def delete(self, name: str) -> None:
        """Remove a blueprint from the store.

        Args:
            name: Blueprint name. No-op if not found.
        """
        bp = self._by_name.pop(name, None)
        if bp is None:
            return
        for fp in bp.fingerprints:
            self._fp_index.pop(fp, None)

    def list_all(self) -> list[StoredBlueprint]:
        """Return all stored blueprints sorted by name.

        Returns:
            Sorted list of stored blueprints.
        """
        return sorted(self._by_name.values(), key=lambda b: b.name)

    def purge_stale(self, ttl_days: int) -> int:
        """No-op for the in-memory store — session-scoped data has no TTL.

        Args:
            ttl_days: Ignored.

        Returns:
            Always 0.
        """
        return 0


class FileBlueprintStore(BlueprintStore):
    """File-system blueprint store — persistent across process restarts.

    Each blueprint is stored as ``{store_dir}/{name}.json``.
    Fingerprint lookup scans all files, which is acceptable at benchmark scale.
    """

    def __init__(self, store_dir: str | Path) -> None:
        """Initialise the file store.

        Args:
            store_dir: Directory where blueprint JSON files are stored.
                       Created on first save if it does not exist.
        """
        self._dir = Path(store_dir)

    def _path(self, name: str) -> Path:
        """Return the JSON file path for a blueprint name.

        Args:
            name: Blueprint name.

        Returns:
            Path to the JSON file.
        """
        return self._dir / f"{name}.json"

    def _load_file(self, path: Path) -> StoredBlueprint | None:
        """Read and deserialise a blueprint JSON file.

        Args:
            path: Path to the JSON file.

        Returns:
            Deserialized blueprint, or ``None`` if the file is missing or corrupt.
        """
        try:
            return StoredBlueprint.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _write_file(self, blueprint: StoredBlueprint) -> None:
        """Serialise and write a blueprint to its JSON file.

        Args:
            blueprint: The blueprint to write.
        """
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path(blueprint.name).write_text(
            blueprint.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def save(self, blueprint: StoredBlueprint) -> None:
        """Persist a blueprint to the file system.

        Args:
            blueprint: The blueprint to save.

        Raises:
            DuplicateBlueprintError: If a blueprint with the same name already exists.
        """
        if self._path(blueprint.name).exists():
            raise DuplicateBlueprintError(blueprint.name)
        self._write_file(blueprint)

    def get_by_name(self, name: str) -> StoredBlueprint | None:
        """Retrieve a blueprint by name.

        Args:
            name: Blueprint name.

        Returns:
            The stored blueprint, or ``None`` if not found.
        """
        return self._load_file(self._path(name))

    def get_by_fingerprint(self, fingerprint: str) -> StoredBlueprint | None:
        """Retrieve a blueprint by task fingerprint (linear scan).

        Args:
            fingerprint: SHA-256 hex digest of a task text.

        Returns:
            The first stored blueprint whose fingerprints include this hash,
            or ``None`` if not found.
        """
        if not self._dir.exists():
            return None
        for path in sorted(self._dir.glob("*.json")):
            bp = self._load_file(path)
            if bp and fingerprint in bp.fingerprints:
                return bp
        return None

    def touch(self, name: str) -> None:
        """Update last_used and increment use_count on disk.

        Args:
            name: Blueprint name. No-op if not found.
        """
        bp = self._load_file(self._path(name))
        if bp is None:
            return
        bp.last_used = datetime.now(timezone.utc)
        bp.use_count += 1
        self._write_file(bp)

    def delete(self, name: str) -> None:
        """Remove a blueprint file from the store.

        Args:
            name: Blueprint name. No-op if file does not exist.
        """
        path = self._path(name)
        if path.exists():
            path.unlink()

    def list_all(self) -> list[StoredBlueprint]:
        """Return all stored blueprints sorted by name.

        Returns:
            Sorted list of stored blueprints.
        """
        if not self._dir.exists():
            return []
        blueprints = []
        for path in sorted(self._dir.glob("*.json")):
            bp = self._load_file(path)
            if bp:
                blueprints.append(bp)
        return blueprints

    def purge_stale(self, ttl_days: int) -> int:
        """Delete blueprints not used within ``ttl_days`` days.

        Args:
            ttl_days: Age threshold in days. Blueprints whose ``last_used``
                      is older than this threshold are removed.

        Returns:
            Number of blueprints purged.
        """
        if not self._dir.exists():
            return 0
        cutoff = datetime.now(timezone.utc).timestamp() - ttl_days * 86400
        purged = 0
        for path in list(self._dir.glob("*.json")):
            bp = self._load_file(path)
            if bp and bp.last_used.timestamp() < cutoff:
                path.unlink()
                purged += 1
        return purged


# Re-export for convenience — avoids importing from two places
__all__ = [
    "BlueprintStore",
    "FileBlueprintStore",
    "MemoryBlueprintStore",
]
