"""Memory-graph linking — delegates to engine/memory_graph.py."""

from __future__ import annotations

from pathlib import Path


def link_memory_to_graph(repo_root: Path, node_id: str, node_type: str, text: str) -> None:
    """Link a memory/decision to related code symbols in the graph."""
    try:
        from ..engine.memory_graph import store_memory_in_graph, store_decision_in_graph
        # node_id format: "memory:5" or "decision:2"
        parts = node_id.split(":")
        num_id = int(parts[1]) if len(parts) > 1 else 0
        if node_type == "decision":
            store_decision_in_graph(repo_root, num_id, text, "")
        else:
            store_memory_in_graph(repo_root, num_id, text, "general")
    except Exception:
        pass


def unlink_from_graph(repo_root: Path, node_id: str) -> None:
    """Remove a memory/decision node from the graph."""
    try:
        from ..engine.memory_graph import evict_memory_from_graph
        parts = node_id.split(":")
        num_id = int(parts[1]) if len(parts) > 1 else 0
        evict_memory_from_graph(repo_root, num_id)
    except Exception:
        pass


def _graph_link_entry(repo_root: Path, node_id: str, node_type: str = "memory", text: str = "") -> None:
    """Link a memory entry to the graph. Delegates to engine."""
    link_memory_to_graph(repo_root, node_id, node_type, text)
