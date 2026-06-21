"""Engine-backed MCP tools — query, context, impact, search against LadybugDB."""

from __future__ import annotations

from pathlib import Path

from ..tool_registry import tool


@tool("mnemo_query",
      "Run a Cypher query against the code knowledge graph. Use for custom graph exploration.",
      properties={
          "cypher": {"type": "string", "description": "Cypher query to execute (e.g., MATCH (c:Class) RETURN c.name LIMIT 10)"},
      },
      required=["cypher"])
def _query(root: Path, args: dict) -> str:
    from ..engine.db import open_db, get_db_path
    if not get_db_path(root).exists():
        return "No code graph found. Run `mnemo init` first."
    _, conn = open_db(root)
    try:
        result = conn.execute(args["cypher"])
        rows = []
        while result.has_next():
            rows.append(result.get_next())
        if not rows:
            return "No results."
        # Format as table
        lines = [str(row) for row in rows[:50]]
        out = "\n".join(lines)
        if len(rows) > 50:
            out += f"\n... ({len(rows)} total results)"
        return out
    except RuntimeError as e:
        return f"Query error: {e}"


@tool("mnemo_impact",
      "Blast radius analysis: what is affected if a symbol changes. Traverses callers/callees N hops deep.",
      properties={
          "symbol": {"type": "string", "description": "Symbol name to analyze impact for"},
          "depth": {"type": "integer", "description": "How many hops to traverse (default 2)"},
          "direction": {"type": "string", "description": "upstream (what calls this), downstream (what this calls), or both (default: upstream)"},
      },
      required=["symbol"])
def _impact(root: Path, args: dict) -> str:
    from ..engine.db import open_db, get_db_path
    if not get_db_path(root).exists():
        return "No code graph found. Run `mnemo init` first."
    _, conn = open_db(root)
    name = args["symbol"]
    depth = int(args.get("depth", 2))
    direction = args.get("direction", "upstream")

    lines = [f"# Impact Analysis: {name} (depth={depth}, {direction})\n"]

    if direction in ("upstream", "both"):
        # What calls this (upstream = what breaks if this changes)
        lines.append("## Upstream (affected if this changes):")
        affected = _traverse_callers(conn, name, depth)
        if affected:
            for sym, d, file in affected:
                lines.append(f"  {'  ' * d}← {sym} ({file})")
        else:
            lines.append("  No upstream callers found.")

    if direction in ("downstream", "both"):
        lines.append("\n## Downstream (dependencies of this):")
        deps = _traverse_callees(conn, name, depth)
        if deps:
            for sym, d, file in deps:
                lines.append(f"  {'  ' * d}→ {sym} ({file})")
        else:
            lines.append("  No downstream dependencies found.")

    # Files affected
    files = set()
    if direction in ("upstream", "both"):
        for sym, _, file in _traverse_callers(conn, name, depth):
            files.add(file)
    lines.append(f"\n**Files potentially affected**: {len(files)}")
    for f in sorted(files)[:10]:
        lines.append(f"  {f}")

    return "\n".join(lines)


def _traverse_callers(conn, name: str, max_depth: int) -> list[tuple[str, int, str]]:
    """BFS upstream: find all callers up to max_depth hops."""
    visited = set()
    results = []
    queue = [(name, 0)]

    while queue:
        current, depth = queue.pop(0)
        if depth >= max_depth:
            continue
        r = conn.execute("MATCH (a:Function)-[:CALLS]->(b:Function) WHERE b.name = $current RETURN a.name, a.file", {"current": current})
        while r.has_next():
            row = r.get_next()
            if row[0] not in visited:
                visited.add(row[0])
                results.append((row[0], depth + 1, row[1]))
                queue.append((row[0], depth + 1))

    return results


def _traverse_callees(conn, name: str, max_depth: int) -> list[tuple[str, int, str]]:
    """BFS downstream: find all callees up to max_depth hops."""
    visited = set()
    results = []
    queue = [(name, 0)]

    while queue:
        current, depth = queue.pop(0)
        if depth >= max_depth:
            continue
        r = conn.execute("MATCH (a:Function)-[:CALLS]->(b:Function) WHERE a.name = $current RETURN b.name, b.file", {"current": current})
        while r.has_next():
            row = r.get_next()
            if row[0] not in visited:
                visited.add(row[0])
                results.append((row[0], depth + 1, row[1]))
                queue.append((row[0], depth + 1))

    return results


@tool("mnemo_communities",
      "List functional areas (Louvain clusters) in the codebase. Shows how code is grouped into modules.",
      properties={
          "name": {"type": "string", "description": "Filter by community name (optional)"},
      })
def _communities(root: Path, args: dict) -> str:
    from ..engine.db import open_db, get_db_path
    if not get_db_path(root).exists():
        return "No code graph found. Run `mnemo init` first."
    _, conn = open_db(root)
    name_filter = args.get("name")

    if name_filter:
        # Show details for a specific community
        r = conn.execute("MATCH (c:Class)-[:MEMBER_OF]->(comm:Community) WHERE comm.name CONTAINS $name_filter RETURN c.name, c.file", {"name_filter": name_filter})
        members = []
        while r.has_next():
            row = r.get_next()
            members.append(f"  {row[0]} ({row[1]})")
        if members:
            return f"# Community: {name_filter}\n\nMembers ({len(members)}):\n" + "\n".join(members)
        return f"No community matching '{name_filter}'."

    # List all communities with member counts
    r = conn.execute("""
        MATCH (c:Class)-[:MEMBER_OF]->(comm:Community)
        RETURN comm.name, count(c) AS cnt
        ORDER BY cnt DESC
        LIMIT 20
    """)
    lines = ["# Code Communities (Leiden clusters)\n"]
    while r.has_next():
        row = r.get_next()
        lines.append(f"  {row[0]}: {row[1]} classes")

    r = conn.execute("""
        MATCH (f:Function)-[:FN_MEMBER_OF]->(comm:Community)
        RETURN comm.name, count(f) AS cnt
        ORDER BY cnt DESC
        LIMIT 10
    """)
    lines.append("")
    while r.has_next():
        row = r.get_next()
        lines.append(f"  {row[0]}: {row[1]} functions")

    return "\n".join(lines)
