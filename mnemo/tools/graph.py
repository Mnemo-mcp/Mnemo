"""Knowledge Graph tools."""

from __future__ import annotations

from pathlib import Path

from ..tool_registry import tool


@tool("mnemo_graph",
      "Query the knowledge graph. Actions: stats, neighbors, traverse, path, find, hubs, why. Use to explore code relationships, dependencies, and impact. The 'why' action traces reason_for edges to explain why an entity exists.",
      properties={
          "action": {"type": "string", "description": "stats, neighbors, traverse, path, find, hubs, or why"},
          "node": {"type": "string", "description": "Node name or ID to query"},
          "target": {"type": "string", "description": "Target node (for path action)"},
          "edge_type": {"type": "string", "description": "Filter by edge type: contains, defines, implements, inherits, calls, depends_on, affects, references, reason_for, owns"},
          "depth": {"type": "integer", "description": "Traversal depth (default 2)"},
          "direction": {"type": "string", "description": "incoming, outgoing, or both (default both)"},
          "type": {"type": "string", "description": "Node type filter for find action"},
          "name": {"type": "string", "description": "Name pattern for find action"},
      },
      required=["action"])
def _graph_query(root: Path, args: dict) -> str:
    from ..graph.query import query_graph
    action = args.get("action", "stats")
    return query_graph(
        root, action,
        node=args.get("node", ""),
        target=args.get("target", ""),
        edge_type=args.get("edge_type"),
        edge_types=args.get("edge_type", "").split(",") if args.get("edge_type") else None,
        depth=int(args.get("depth", 2)),
        direction=args.get("direction", "both"),
        type=args.get("type"),
        name=args.get("name"),
    )
