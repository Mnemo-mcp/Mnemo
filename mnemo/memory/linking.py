"""Memory-to-graph linking operations."""

from __future__ import annotations

from pathlib import Path

from ..utils.logger import get_logger

logger = get_logger("memory.linking")


def _graph_link_entry(repo_root: Path, node_id: str, node_type: str, text: str) -> None:
    """Auto-link a new memory/decision node to the knowledge graph."""
    try:
        from ..graph.local import LocalGraph
        from ..graph import Node, Edge

        graph = LocalGraph(repo_root)
        if not graph.exists():
            return
        graph.upsert_node(Node(id=node_id, type=node_type, name=text[:80], properties={"full_text": text}))
        edge_type = "reason_for" if node_type == "decision" else "references"
        for nid, data in graph.graph.nodes(data=True):
            if data.get("type") in ("class", "service", "interface") and len(data.get("name", "")) >= 4:
                if data["name"] in text:
                    graph.upsert_edge(Edge(source=node_id, target=nid, type=edge_type))
        graph.save()
    except Exception as exc:
        logger.debug(f"Failed to link memory to graph: {exc}")
