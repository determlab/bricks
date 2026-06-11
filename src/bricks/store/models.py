"""Data models for the Blueprint store."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class StoredBlueprint(BaseModel):
    """A validated blueprint persisted in the store.

    Attributes:
        name: Unique blueprint name (taken from the ``name:`` field in YAML).
        yaml: Raw YAML text of the validated blueprint.
        fingerprints: SHA-256 hashes of task texts that produced this blueprint.
        created_at: UTC timestamp when the blueprint was first saved.
        last_used: UTC timestamp of the most recent cache hit or save.
        use_count: Number of times this blueprint was served from cache.
    """

    name: str
    yaml: str
    fingerprints: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    use_count: int = 0


def task_fingerprint(task: str) -> str:
    """Return a deterministic SHA-256 hex digest for a task text.

    Args:
        task: Natural language task description.

    Returns:
        64-character lowercase hex string.
    """
    return hashlib.sha256(task.encode("utf-8")).hexdigest()
