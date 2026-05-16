"""Knowledge Graph tools — powered by engine/ LadybugDB."""

from __future__ import annotations

from pathlib import Path

from ..tool_registry import tool


@tool("mnemo_graph",
      "Query the knowledge graph. Actions: stats, neighbors, find. Use to explore code relationships and dependencies.",
      properties={
          "action": {"type": "string", "description": "stats, neighbors, or find"},
          "node": {"type": "string", "description": "Node name to query neighbors for"},
          "type": {"type": "string", "description": "Node type filter: class, function, file, project, community"},
          "name": {"type": "string", "description": "Name pattern for find action"},
      },
      required=["action"])
def _graph_query(root: Path, args: dict) -> str:
    from ..engine.db import open_db, get_db_path

    if not get_db_path(root).exists():
        return "No graph database. Run `mnemo init` to index."

    _, conn = open_db(root)
    action = args.get("action", "stats")

    if action == "stats":
        lines = []
        for label in ("File", "Class", "Function", "Project", "Community"):
            r = conn.execute(f"MATCH (n:{label}) RETURN count(n)")
            lines.append(f"{label}: {r.get_next()[0]}")
        r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
        lines.append(f"Edges: {r.get_next()[0]}")
        return "\n".join(lines)

    elif action == "neighbors":
        node = args.get("node", "")
        if not node:
            return "Provide 'node' parameter."
        results = []
        for rel in ("CALLS", "HAS_METHOD", "MEMBER_OF"):
            r = conn.execute(f"MATCH (a)-[e:{rel}]->(b) WHERE a.name CONTAINS '{node}' RETURN a.name, b.name LIMIT 10")
            while r.has_next():
                row = r.get_next()
                results.append(f"{row[0]} --{rel}--> {row[1]}")
            r = conn.execute(f"MATCH (a)-[e:{rel}]->(b) WHERE b.name CONTAINS '{node}' RETURN a.name, b.name LIMIT 10")
            while r.has_next():
                row = r.get_next()
                results.append(f"{row[0]} --{rel}--> {row[1]}")
        return "\n".join(results) if results else f"No neighbors found for '{node}'."

    elif action == "find":
        node_type = args.get("type", "Class")
        name = args.get("name", "")
        if not name:
            return "Provide 'name' parameter."
        label = node_type.capitalize()
        r = conn.execute(f"MATCH (n:{label}) WHERE n.name CONTAINS '{name}' RETURN n.id, n.name LIMIT 20")
        results = []
        while r.has_next():
            row = r.get_next()
            results.append(f"{row[1]} ({row[0]})")
        return "\n".join(results) if results else f"No {label} matching '{name}'."

    return f"Unknown action: {action}"
