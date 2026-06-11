"""Brick discovery: auto-register bricks from Python modules."""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
from pathlib import Path
from types import ModuleType
from typing import Any

from bricks.core.brick import BaseBrick
from bricks.core.models import BrickMeta
from bricks.core.registry import BrickRegistry

logger = logging.getLogger(__name__)


class BrickDiscovery:
    """Discovers and registers Bricks from Python modules or packages.

    Scans a module (or directory of modules) for:
    - Functions decorated with ``@brick`` (have ``__brick_meta__`` attribute).
    - Subclasses of ``BaseBrick`` with a ``Meta`` inner class.
    """

    def __init__(self, registry: BrickRegistry) -> None:
        """Initialise the discovery engine.

        Args:
            registry: The registry to register discovered bricks into.
        """
        self._registry = registry

    def discover_module(self, module: ModuleType) -> list[str]:
        """Discover and register all bricks in a Python module.

        Args:
            module: An already-imported Python module.

        Returns:
            A list of registered brick names found in this module.
        """
        registered: list[str] = []
        for _attr_name, obj in inspect.getmembers(module):
            name = self._try_register(obj)
            if name is not None:
                registered.append(name)
        return registered

    def discover_path(self, path: Path) -> list[str]:
        """Discover and register all bricks in a Python file.

        Args:
            path: Path to a .py file.

        Returns:
            A list of registered brick names found in this file.

        Raises:
            ImportError: If the file cannot be imported.
            FileNotFoundError: If the path does not exist.
        """
        if not path.exists():
            raise FileNotFoundError(f"Module file not found: {path}")
        module_name = path.stem
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load spec for {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return self.discover_module(module)

    def discover_package(self, package_path: Path) -> list[str]:
        """Discover bricks in all .py files in a directory (non-recursive).

        Args:
            package_path: Path to a directory containing .py files.

        Returns:
            A list of all registered brick names found.

        Raises:
            NotADirectoryError: If the path is not a directory.
        """
        if not package_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {package_path}")
        registered: list[str] = []
        for py_file in sorted(package_path.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            try:
                registered.extend(self.discover_path(py_file))
            except Exception as exc:
                logger.warning("Failed to discover bricks in %s: %s", py_file, exc)
        return registered

    def _try_register(self, obj: Any) -> str | None:
        """Attempt to register a single object as a brick.

        Args:
            obj: Any Python object (function, class, etc.).

        Returns:
            The registered brick name, or None if not a registrable brick.
        """
        # Function brick: has __brick_meta__ attribute
        if callable(obj) and hasattr(obj, "__brick_meta__"):
            meta: BrickMeta = obj.__brick_meta__
            if not self._registry.has(meta.name):
                self._registry.register(meta.name, obj, meta)
                return meta.name
            return None

        # Class-based brick: subclass of BaseBrick (not BaseBrick itself)
        if inspect.isclass(obj) and issubclass(obj, BaseBrick) and obj is not BaseBrick:
            meta_cls = getattr(obj, "Meta", None)
            if meta_cls is None:
                return None
            brick_name = getattr(meta_cls, "name", obj.__name__)
            if self._registry.has(brick_name):
                return None
            brick_meta = BrickMeta(
                name=brick_name,
                tags=getattr(meta_cls, "tags", []),
                destructive=getattr(meta_cls, "destructive", False),
                idempotent=getattr(meta_cls, "idempotent", True),
                description=getattr(meta_cls, "description", ""),
            )
            instance = obj()
            self._registry.register(brick_name, instance.execute, brick_meta)
            return brick_name

        return None
