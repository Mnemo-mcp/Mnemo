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


@tool("mnemo_symbol",
      "Get 360° context for a symbol: what file defines it, its methods, what calls it, what it calls, which community it belongs to.",
      properties={
          "symbol": {"type": "string", "description": "Symbol name (class, function, or method name)"},
      },
      required=["symbol"])
def _context(root: Path, args: dict) -> str:
    from ..engine.db import open_db, get_db_path
    if not get_db_path(root).exists():
        return "No code graph found. Run `mnemo init` first."
    _, conn = open_db(root)
    name = args["symbol"]
    lines = [f"# Context: {name}\n"]

    # Find the symbol (class or function)
    r = conn.execute(f"MATCH (c:Class) WHERE c.name = '{name}' RETURN c.id, c.file, c.implements")
    found = False
    while r.has_next():
        row = r.get_next()
        lines.append(f"**Class** `{name}` in `{row[1]}`")
        if row[2]:
            lines.append(f"  Implements: {row[2]}")
        found = True

    if not found:
        r = conn.execute(f"MATCH (f:Function) WHERE f.name = '{name}' RETURN f.id, f.file, f.signature")
        while r.has_next():
            row = r.get_next()
            lines.append(f"**Function** `{name}` in `{row[1]}`")
            lines.append(f"  Signature: {row[2]}")
            found = True

    if not found:
        return f"Symbol '{name}' not found in the graph."

    # Methods (if class)
    r = conn.execute(f"MATCH (c:Class {{name: '{name}'}})-[:HAS_METHOD]->(m:Method) RETURN m.name, m.signature")
    methods = []
    while r.has_next():
        row = r.get_next()
        methods.append(f"  .{row[0]}() — {row[1][:60]}")
    if methods:
        lines.append(f"\n**Methods** ({len(methods)}):")
        lines.extend(methods[:15])
        if len(methods) > 15:
            lines.append(f"  ... +{len(methods)-15} more")

    # What calls this symbol
    r = conn.execute(f"MATCH (a:Function)-[c:CALLS]->(b:Function) WHERE b.name = '{name}' RETURN a.name, a.file, c.confidence")
    callers = []
    while r.has_next():
        row = r.get_next()
        callers.append(f"  ← {row[0]} ({row[1]}) [conf: {row[2]}]")
    if callers:
        lines.append(f"\n**Called by** ({len(callers)}):")
        lines.extend(callers[:10])

    # What this symbol calls
    r = conn.execute(f"MATCH (a:Function)-[c:CALLS]->(b:Function) WHERE a.name = '{name}' RETURN b.name, b.file, c.confidence")
    callees = []
    while r.has_next():
        row = r.get_next()
        callees.append(f"  → {row[0]} ({row[1]}) [conf: {row[2]}]")
    if callees:
        lines.append(f"\n**Calls** ({len(callees)}):")
        lines.extend(callees[:10])

    # Community membership
    r = conn.execute(f"MATCH (c:Class {{name: '{name}'}})-[:MEMBER_OF]->(comm:Community) RETURN comm.name")
    while r.has_next():
        lines.append(f"\n**Community**: {r.get_next()[0]}")

    return "\n".join(lines)


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
        r = conn.execute(f"MATCH (a:Function)-[:CALLS]->(b:Function) WHERE b.name = '{current}' RETURN a.name, a.file")
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
        r = conn.execute(f"MATCH (a:Function)-[:CALLS]->(b:Function) WHERE a.name = '{current}' RETURN b.name, b.file")
        while r.has_next():
            row = r.get_next()
            if row[0] not in visited:
                visited.add(row[0])
                results.append((row[0], depth + 1, row[1]))
                queue.append((row[0], depth + 1))

    return results


@tool("mnemo_find",
      "Search the code graph for symbols by name pattern. Returns matching classes, functions, and methods.",
      properties={
          "query": {"type": "string", "description": "Search query (name or pattern to find)"},
          "type": {"type": "string", "description": "Filter by type: class, function, method, file (optional)"},
          "limit": {"type": "integer", "description": "Max results (default 20)"},
      },
      required=["query"])
def _search(root: Path, args: dict) -> str:
    from ..engine.db import open_db, get_db_path
    if not get_db_path(root).exists():
        return "No code graph found. Run `mnemo init` first."
    _, conn = open_db(root)
    query = args["query"]
    type_filter = args.get("type")
    limit = int(args.get("limit", 20))

    results = []

    if not type_filter or type_filter == "class":
        r = conn.execute(f"MATCH (c:Class) WHERE c.name CONTAINS '{query}' RETURN 'class' AS type, c.name, c.file LIMIT {limit}")
        while r.has_next():
            row = r.get_next()
            results.append(f"  [{row[0]}] {row[1]} — {row[2]}")

    if not type_filter or type_filter == "function":
        r = conn.execute(f"MATCH (f:Function) WHERE f.name CONTAINS '{query}' RETURN 'function' AS type, f.name, f.file LIMIT {limit}")
        while r.has_next():
            row = r.get_next()
            results.append(f"  [{row[0]}] {row[1]} — {row[2]}")

    if not type_filter or type_filter == "method":
        r = conn.execute(f"MATCH (m:Method) WHERE m.name CONTAINS '{query}' RETURN 'method' AS type, m.name, m.file LIMIT {limit}")
        while r.has_next():
            row = r.get_next()
            results.append(f"  [{row[0]}] {row[1]} — {row[2]}")

    if not type_filter or type_filter == "file":
        r = conn.execute(f"MATCH (f:File) WHERE f.path CONTAINS '{query}' RETURN 'file' AS type, f.path, f.language LIMIT {limit}")
        while r.has_next():
            row = r.get_next()
            results.append(f"  [{row[0]}] {row[1]} ({row[2]})")

    if not results:
        return f"No results for '{query}'."

    return f"# Search: '{query}' ({len(results)} results)\n\n" + "\n".join(results[:limit])


@tool("mnemo_communities",
      "List functional areas (Leiden clusters) in the codebase. Shows how code is grouped into modules.",
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
        r = conn.execute(f"MATCH (c:Class)-[:MEMBER_OF]->(comm:Community) WHERE comm.name CONTAINS '{name_filter}' RETURN c.name, c.file")
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
