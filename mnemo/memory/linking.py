"""Memory-to-graph linking operations."""

from __future__ import annotations

from pathlib import Path

from ..utils.logger import get_logger

logger = get_logger("memory.linking")


def _graph_link_entry(repo_root: Path, node_id: str, node_type: str, text: str) -> None:
    """Auto-link a new memory/decision node to the knowledge graph (both old + new engine)."""
    # New engine: LadybugDB
    try:
        from ..engine.memory_graph import store_memory_in_graph, store_decision_in_graph
        # Extract numeric ID from node_id like "memory:5" or "decision:3"
        parts = node_id.split(":")
        num_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        if node_type == "decision":
            store_decision_in_graph(repo_root, num_id, text, "")
        else:
            category = "general"
            store_memory_in_graph(repo_root, num_id, text, category)
    except Exception as exc:
        logger.debug(f"LadybugDB link failed (non-fatal): {exc}")

    # Old engine: NetworkX (kept for backward compat until fully removed)
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
        logger.debug(f"NetworkX link failed (non-fatal): {exc}")
