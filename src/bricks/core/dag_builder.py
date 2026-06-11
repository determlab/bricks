"""DAGBuilder — converts a flat list of traced Nodes into a DAG."""

from __future__ import annotations

from bricks.core.dag import DAG
from bricks.core.dsl import Node


class DAGBuilder:
    """Builds a :class:`~bricks.core.dag.DAG` from traced :class:`~bricks.core.dsl.Node` objects.

    Resolves dependency edges by inspecting:

    - ``params`` values that are themselves :class:`~bricks.core.dsl.Node` objects,
      including Nodes nested inside list or dict values (brick→brick data flow).
      Must stay symmetric with :func:`bricks.core.dag._resolve_param`, which
      recurses into the same containers when writing reference strings.
    - ``items`` field of ``for_each`` nodes when it is a
      :class:`~bricks.core.dsl.Node`.

    Example::

        from bricks.core.dsl import _tracer, step
        from bricks.core.dag_builder import DAGBuilder

        _tracer.start()
        a = step.load(path="data.csv")
        b = step.clean(data=a)
        _tracer.stop()

        dag = DAGBuilder().build(_tracer.get_nodes())
    """

    def build(self, nodes: list[Node], root: Node | None = None) -> DAG:
        """Convert a flat list of traced nodes into a DAG.

        Registers every node, resolves dependency edges, and sets the root.

        Args:
            nodes: Flat list of :class:`~bricks.core.dsl.Node` objects, typically
                from :meth:`~bricks.core.dsl.ExecutionTracer.get_nodes`.
            root: The final/return node. Defaults to the last node in *nodes*.

        Returns:
            A :class:`~bricks.core.dag.DAG` with all nodes registered and
            ``edges`` / ``depends_on`` populated.
        """
        dag = DAG()
        node_map: dict[str, Node] = {}

        for node in nodes:
            node_map[node.id] = node
            dag.nodes[node.id] = node
            dag.edges[node.id] = []

        for node in nodes:
            deps = self._find_dependencies(node, node_map)
            dag.edges[node.id] = deps
            node.depends_on = deps

        if root is not None:
            dag.root_id = root.id
        elif nodes:
            dag.root_id = nodes[-1].id

        return dag

    def _find_dependencies(self, node: Node, node_map: dict[str, Node]) -> list[str]:
        """Return ids of all nodes that *node* directly depends on.

        Args:
            node: The node to inspect.
            node_map: All registered nodes keyed by id.

        Returns:
            List of dependency node ids (may be empty).
        """
        deps: list[str] = []

        if node.type == "brick":
            for value in node.params.values():
                self._collect_node_deps(value, node_map, deps)

        elif node.type == "for_each" and isinstance(node.items, Node) and node.items.id in node_map:
            deps.append(node.items.id)

        # branch — sub-nodes produced by if_true/if_false are already in the
        # traced list; no extra wiring needed at this stage.

        return deps

    def _collect_node_deps(
        self,
        value: object,
        node_map: dict[str, Node],
        deps: list[str],
    ) -> None:
        """Append dep ids from any :class:`Node` refs reachable inside *value*.

        Recurses into list and dict containers, mirroring
        :func:`bricks.core.dag._resolve_param`. De-duplicates while preserving
        first-seen order.
        """
        if isinstance(value, Node):
            if value.id in node_map and value.id not in deps:
                deps.append(value.id)
            return
        if isinstance(value, list):
            for item in value:
                self._collect_node_deps(item, node_map, deps)
            return
        if isinstance(value, dict):
            for item in value.values():
                self._collect_node_deps(item, node_map, deps)
