"""Bricks - Deterministic execution engine for typed Python building blocks."""

from bricks.api import build_default_registry, run_blueprint
from bricks.core.dag import DAG
from bricks.core.dag_builder import DAGBuilder
from bricks.core.dsl import Node, branch, flow, for_each, step
from bricks.core.engine import DAGExecutionEngine

__version__ = "0.5.0-dev"

__all__ = [
    "DAG",
    "DAGBuilder",
    "DAGExecutionEngine",
    "Node",
    "__version__",
    "branch",
    "build_default_registry",
    "flow",
    "for_each",
    "run_blueprint",
    "step",
]


def __getattr__(name: str) -> object:
    """Give a migration hint for the AI facade that moved to ``bricks_ai``.

    Args:
        name: The attribute name being accessed.

    Returns:
        Never returns for known moved names; raises instead.

    Raises:
        ImportError: If ``Bricks`` is requested — it moved to ``bricks_ai``.
        AttributeError: For any other unknown attribute.
    """
    if name == "Bricks":
        raise ImportError(
            "The 'Bricks' AI facade moved to the bricks_ai package in the "
            "engine/AI split. Use: from bricks_ai import Bricks "
            '(pip install "bricks-ai[ai]")'
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
