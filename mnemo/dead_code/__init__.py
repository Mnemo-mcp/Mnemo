"""Dead code detector — uses engine/ graph CALLS edges to find unreferenced symbols."""

from __future__ import annotations

from pathlib import Path


def detect_dead_code(repo_root: Path) -> str:
    """Detect potentially unused classes and functions via graph analysis."""
    from ..engine.db import open_db, get_db_path

    if not get_db_path(repo_root).exists():
        return "No graph database. Run `mnemo init` to index the repo first."

    _, conn = open_db(repo_root)

    # Functions with no incoming CALLS edges and not in test files
    unused_functions = []
    result = conn.execute("""
        MATCH (f:Function)
        WHERE NOT ()-[:CALLS]->(f)
        AND NOT f.file CONTAINS 'test'
        AND NOT f.name STARTS WITH '_'
        AND NOT f.name IN ['main', 'cli', 'setup', 'configure']
        RETURN f.name, f.file, f.signature
    """)
    while result.has_next():
        row = result.get_next()
        unused_functions.append({"name": row[0], "file": row[1], "signature": row[2] or row[0], "type": "function"})

    # Classes with no incoming edges (not referenced by CALLS, EXTENDS, IMPLEMENTS)
    unused_classes = []
    result = conn.execute("""
        MATCH (c:Class)
        WHERE NOT ()-[:CALLS]->(c)
        AND NOT ()-[:EXTENDS]->(c)
        AND NOT ()-[:IMPLEMENTS]->(c)
        AND NOT c.file CONTAINS 'test'
        AND NOT c.name STARTS WITH '_'
        RETURN c.name, c.file, c.implements
    """)
    while result.has_next():
        row = result.get_next()
        unused_classes.append({"name": row[0], "file": row[1], "implements": row[2] or "", "type": "class"})

    unused = unused_classes + unused_functions
    if not unused:
        return "No potentially dead code detected."

    # Build report
    lines = [f"# Potentially Unused Code ({len(unused)} symbols)\n"]
    lines.append("These symbols have no incoming CALLS/EXTENDS/IMPLEMENTS edges in the graph.\n")

    by_file: dict[str, list[dict]] = {}
    for sym in unused:
        by_file.setdefault(sym["file"], []).append(sym)

    for file, syms in sorted(by_file.items()):
        lines.append(f"## `{file}`\n")
        for s in syms:
            lines.append(f"- **{s['type']}** `{s['name']}` — `{s.get('signature', s['name'])}`")
        lines.append("")

    lines.append("---")
    lines.append("*Note: Some may be used via reflection, DI, dynamic dispatch, or external consumers.*")
    return "\n".join(lines)
