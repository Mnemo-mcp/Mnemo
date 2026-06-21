"""Code Health Score — aggregates from engine/ graph stats."""

from __future__ import annotations

import json
from pathlib import Path

from ..config import mnemo_path


def system_health(repo_root: Path) -> dict:
    """Return system health metrics from engine and memory."""
    import resource
    mem_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)

    mnemo_dir = mnemo_path(repo_root)
    memories = 0
    decisions = 0
    graph_nodes = 0
    graph_edges = 0
    dir_size_kb = 0.0
    warnings: list[str] = []

    if mnemo_dir.exists():
        mem_file = mnemo_dir / "memory.json"
        if mem_file.exists():
            try:
                memories = len(json.loads(mem_file.read_text()))
            except (json.JSONDecodeError, OSError):
                pass
        dec_file = mnemo_dir / "decisions.json"
        if dec_file.exists():
            try:
                decisions = len(json.loads(dec_file.read_text()))
            except (json.JSONDecodeError, OSError):
                pass
        for f in mnemo_dir.rglob("*"):
            if f.is_file():
                try:
                    dir_size_kb += f.stat().st_size / 1024
                except OSError:
                    pass

    # Get graph stats from engine
    try:
        from ..engine.db import open_db, get_db_path
        if get_db_path(repo_root).exists():
            _, conn = open_db(repo_root)
            r = conn.execute("MATCH (n) RETURN count(n)")
            graph_nodes = r.get_next()[0] if r.has_next() else 0
            r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
            graph_edges = r.get_next()[0] if r.has_next() else 0
    except Exception:
        pass

    if dir_size_kb > 100 * 1024:
        warnings.append(f"Total .mnemo/ size exceeds 100MB ({dir_size_kb / 1024:.1f} MB)")

    return {
        "memory_mb": mem_mb,
        "memories": memories,
        "decisions": decisions,
        "graph_nodes": graph_nodes,
        "graph_edges": graph_edges,
        "mnemo_dir_size_kb": dir_size_kb,
        "warnings": warnings,
    }


def calculate_health(repo_root: Path) -> str:
    """Calculate code health from engine graph."""
    from ..engine.db import open_db, get_db_path

    lines = ["# Code Health Report\n"]

    # System health
    sh = system_health(repo_root)
    lines.append("## System Health")
    lines.append(f"- **Process memory:** {sh['memory_mb']:.1f} MB")
    lines.append(f"- **Memories:** {sh['memories']}")
    lines.append(f"- **Decisions:** {sh['decisions']}")
    lines.append(f"- **Graph:** {sh['graph_nodes']} nodes, {sh['graph_edges']} edges")
    lines.append(f"- **.mnemo/ size:** {sh['mnemo_dir_size_kb']:.0f} KB")
    lines.append("")

    if not get_db_path(repo_root).exists():
        lines.append("No graph database. Run `mnemo init` to index.")
        return "\n".join(lines)

    _, conn = open_db(repo_root)

    # File stats by language
    lines.append("## Codebase Stats")
    r = conn.execute("MATCH (f:File) RETURN f.language, count(f) ORDER BY count(f) DESC")
    while r.has_next():
        row = r.get_next()
        lines.append(f"- **{row[0]}:** {row[1]} files")
    lines.append("")

    # Project breakdown
    r = conn.execute("MATCH (p:Project) RETURN p.name, p.language")
    projects = []
    while r.has_next():
        row = r.get_next()
        projects.append(f"{row[0]} ({row[1]})")
    if projects:
        lines.append(f"## Projects ({len(projects)})")
        for p in projects:
            lines.append(f"- {p}")
        lines.append("")

    # Complexity hotspots: files with most defined symbols
    lines.append("## Complexity Hotspots (most symbols per file)")
    r = conn.execute("""
        MATCH (f:File)-[:FILE_DEFINES_FUNCTION]->(fn:Function)
        RETURN f.path, count(fn) AS cnt
        ORDER BY cnt DESC LIMIT 10
    """)
    while r.has_next():
        row = r.get_next()
        lines.append(f"- `{row[0]}` — {row[1]} functions")
    lines.append("")

    # Coupling hotspots: files with most imports
    lines.append("## Coupling Hotspots (most imports)")
    r = conn.execute("""
        MATCH (a:File)-[:IMPORTS]->(b:File)
        RETURN a.path, count(b) AS cnt
        ORDER BY cnt DESC LIMIT 10
    """)
    while r.has_next():
        row = r.get_next()
        lines.append(f"- `{row[0]}` — imports {row[1]} files")
    lines.append("")

    # Community count
    r = conn.execute("MATCH (c:Community) RETURN count(c)")
    comm_count = r.get_next()[0] if r.has_next() else 0
    lines.append(f"## Architecture: {comm_count} detected communities")

    if sh["warnings"]:
        lines.append("\n## ⚠️ Warnings")
        for w in sh["warnings"]:
            lines.append(f"- {w}")

    return "\n".join(lines)
