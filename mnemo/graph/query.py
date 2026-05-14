"""Graph query — MCP tool interface for knowledge graph queries."""

from __future__ import annotations

from pathlib import Path

from . import Node
from .local import LocalGraph


def query_graph(repo_root: Path, action: str, **kwargs) -> str:
    """Execute a graph query and return formatted markdown."""
    graph = LocalGraph(repo_root)
    if not graph.exists():
        return "No knowledge graph found. Run `mnemo map` to build it."

    if action == "stats":
        return _format_stats(graph)
    elif action == "neighbors":
        return _format_neighbors(graph, kwargs.get("node", ""), kwargs.get("edge_type"), kwargs.get("direction", "both"))
    elif action == "traverse":
        return _format_traverse(graph, kwargs.get("node", ""), kwargs.get("depth", 2), kwargs.get("edge_types"), kwargs.get("direction", "both"))
    elif action == "path":
        return _format_path(graph, kwargs.get("node", ""), kwargs.get("target", ""))
    elif action == "find":
        return _format_find(graph, kwargs.get("type"), kwargs.get("name"))
    elif action == "hubs":
        return _format_hubs(graph)
    elif action == "why":
        return _format_why(graph, kwargs.get("node", ""))
    else:
        return f"Unknown action: {action}. Use: stats, neighbors, traverse, path, find, hubs, why"


def _resolve_node_id(graph: LocalGraph, name: str) -> str | None:
    """Resolve a human-friendly name to a node ID."""
    # Try exact ID first
    if graph.get_node(name):
        return name
    # Try common prefixes
    for prefix in ("class:", "service:", "interface:", "file:", "method:", "package:", "person:", "function:"):
        candidate = f"{prefix}{name}"
        if graph.get_node(candidate):
            return candidate
    # Fuzzy: find nodes containing the name
    matches = graph.find_nodes(name_pattern=name)
    if matches:
        return matches[0].id
    return None


def _format_stats(graph: LocalGraph) -> str:
    s = graph.stats()
    lines = ["# Knowledge Graph Stats\n", f"- **Nodes:** {s['nodes']}", f"- **Edges:** {s['edges']}\n", "## Node Types"]
    for t, count in sorted(s.get("node_types", {}).items(), key=lambda x: x[1], reverse=True):
        lines.append(f"- {t}: {count}")
    lines.append("\n## Edge Types")
    for t, count in sorted(s.get("edge_types", {}).items(), key=lambda x: x[1], reverse=True):
        lines.append(f"- {t}: {count}")
    return "\n".join(lines)


def _format_neighbors(graph: LocalGraph, name: str, edge_type: str | None, direction: str) -> str:
    node_id = _resolve_node_id(graph, name)
    if not node_id:
        return f"Node '{name}' not found in graph."
    node = graph.get_node(node_id)
    neighbors = graph.get_neighbors(node_id, edge_type=edge_type, direction=direction)
    if not neighbors:
        return f"No neighbors for '{node.name}' (type: {node.type})."

    lines = [f"# Neighbors of `{node.name}` ({node.type})\n"]

    outgoing = [(e, n) for e, n in neighbors if e.source == node_id]
    incoming = [(e, n) for e, n in neighbors if e.target == node_id]

    if outgoing:
        lines.append("## Outgoing")
        for edge, neighbor in outgoing:
            lines.append(f"- `{node.name}` --{edge.type}--> `{neighbor.name}` ({neighbor.type})")

    if incoming:
        lines.append("\n## Incoming")
        for edge, neighbor in incoming:
            lines.append(f"- `{neighbor.name}` ({neighbor.type}) --{edge.type}--> `{node.name}`")

    return "\n".join(lines)


def _format_traverse(graph: LocalGraph, name: str, depth: int, edge_types: list[str] | None, direction: str) -> str:
    node_id = _resolve_node_id(graph, name)
    if not node_id:
        return f"Node '{name}' not found in graph."
    node = graph.get_node(node_id)
    visited = graph.traverse(node_id, depth=depth, edge_types=edge_types, direction=direction)

    # Remove start node from results
    visited.pop(node_id, None)
    if not visited:
        return f"No connected nodes within {depth} hops of `{node.name}`."

    lines = [f"# Traversal from `{node.name}` (depth={depth}, direction={direction})\n"]

    # Group by type
    by_type: dict[str, list[Node]] = {}
    for n in visited.values():
        by_type.setdefault(n.type, []).append(n)

    for ntype, nodes in sorted(by_type.items()):
        lines.append(f"## {ntype} ({len(nodes)})")
        for n in sorted(nodes, key=lambda x: x.name)[:20]:
            lines.append(f"- `{n.name}`")
        if len(nodes) > 20:
            lines.append(f"  ... +{len(nodes) - 20} more")
        lines.append("")

    return "\n".join(lines)


def _format_path(graph: LocalGraph, name: str, target: str) -> str:
    import networkx as nx

    node_id = _resolve_node_id(graph, name)
    target_id = _resolve_node_id(graph, target)
    if not node_id:
        return f"Source node '{name}' not found."
    if not target_id:
        return f"Target node '{target}' not found."

    try:
        path = nx.shortest_path(graph.graph, node_id, target_id)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        # Try undirected
        try:
            path = nx.shortest_path(graph.graph.to_undirected(), node_id, target_id)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return f"No path between `{name}` and `{target}`."

    lines = [f"# Path: `{name}` → `{target}` ({len(path) - 1} hops)\n"]
    for i, nid in enumerate(path):
        node = graph.get_node(nid)
        prefix = "→ " if i > 0 else "⬤ "
        lines.append(f"{prefix}`{node.name}` ({node.type})")
        if i < len(path) - 1:
            # Find edge between this and next
            next_id = path[i + 1]
            for _, _, data in graph.graph.edges(nid, data=True):
                pass  # just show the hop
            edges = graph.graph.get_edge_data(nid, next_id)
            if edges:
                etype = list(edges.values())[0].get("type", "?")
                lines.append(f"  | --{etype}-->")

    return "\n".join(lines)


def _format_find(graph: LocalGraph, type: str | None, name: str | None) -> str:
    nodes = graph.find_nodes(type=type, name_pattern=name)
    if not nodes:
        query = f"type={type}" if type else f"name='{name}'"
        return f"No nodes found matching {query}."

    lines = [f"# Found {len(nodes)} nodes\n"]
    by_type: dict[str, list[Node]] = {}
    for n in nodes:
        by_type.setdefault(n.type, []).append(n)

    for ntype, type_nodes in sorted(by_type.items()):
        lines.append(f"## {ntype} ({len(type_nodes)})")
        for n in sorted(type_nodes, key=lambda x: x.name)[:30]:
            lines.append(f"- `{n.name}`")
        if len(type_nodes) > 30:
            lines.append(f"  ... +{len(type_nodes) - 30} more")
        lines.append("")

    return "\n".join(lines)


def _format_hubs(graph: LocalGraph) -> str:
    """Find the most connected nodes (hubs) in the graph."""
    g = graph.graph
    if not g.nodes:
        return "Graph is empty."

    # Calculate degree (in + out)
    degrees = [(nid, g.in_degree(nid) + g.out_degree(nid)) for nid in g.nodes]
    degrees.sort(key=lambda x: x[1], reverse=True)

    lines = ["# Graph Hubs (most connected nodes)\n"]
    for nid, degree in degrees[:15]:
        node = graph.get_node(nid)
        if node:
            lines.append(f"- `{node.name}` ({node.type}) — {degree} connections")

    return "\n".join(lines)


def _format_why(graph: LocalGraph, name: str) -> str:
    """Find why an entity exists by traversing reason_for edges from decisions."""
    node_id = _resolve_node_id(graph, name)
    if not node_id:
        return f"Node '{name}' not found in graph."
    node = graph.get_node(node_id)

    # Find incoming reason_for edges (decisions that explain this entity)
    reasons = graph.get_neighbors(node_id, edge_type="reason_for", direction="incoming")

    # Also check references edges from decisions
    references = graph.get_neighbors(node_id, edge_type="references", direction="incoming")
    decision_refs = [(e, n) for e, n in references if n.type == "decision"]

    all_reasons = reasons + decision_refs

    if not all_reasons:
        return f"No recorded reasons for why `{node.name}` ({node.type}) exists. Use `mnemo_decide` to record architectural decisions that reference this entity."

    lines = [f"# Why does `{node.name}` exist?\n"]
    for edge, reason_node in all_reasons:
        full_text = reason_node.properties.get("full_text", reason_node.name)
        lines.append(f"- **{reason_node.type}**: {full_text}")
    return "\n".join(lines)
