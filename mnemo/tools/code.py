"""Code intelligence tools — powered by engine/."""

from __future__ import annotations

from pathlib import Path

from ..tool_registry import tool


@tool("mnemo_lookup",
      "Look up detailed information about a code symbol, service, or project. Returns 360° context: for classes — methods, callers, callees; for services/projects — all classes with their methods and relationships.",
      properties={
          "symbol": {"type": "string", "description": "Symbol name, service name, or folder prefix to look up"},
          "file": {"type": "string", "description": "Optional file path to scope the lookup"},
      },
      required=["symbol"])
def _lookup(root: Path, args: dict) -> str:
    from ..engine.db import open_db, get_db_path

    if not get_db_path(root).exists():
        return "No graph database. Run `mnemo init` first."

    _, conn = open_db(root)
    symbol = args.get("symbol", "")
    lines = []

    # Try as project/service first
    r = conn.execute(f"MATCH (p:Project) WHERE p.name CONTAINS '{symbol}' RETURN p.id, p.name, p.language, p.path")
    if r.has_next():
        row = r.get_next()
        proj_path = row[3]
        lines.append(f"# Service: {row[1]} ({row[2]})")
        lines.append(f"- Path: `{proj_path}/`")

        # All classes in this project
        prefix = f"{proj_path}/" if proj_path else ""
        r2 = conn.execute(f"MATCH (c:Class) WHERE c.file STARTS WITH '{prefix}' RETURN c.name, c.file, c.implements")
        classes = []
        while r2.has_next():
            classes.append(r2.get_next())
        lines.append(f"- Classes ({len(classes)}):")
        for cname, cfile, cimpl in classes[:30]:
            impl = f" : {cimpl}" if cimpl else ""
            # Get methods for this class
            r3 = conn.execute(f"MATCH (c:Class {{name: '{cname}', file: '{cfile}'}})-[:HAS_METHOD]->(m:Method) RETURN m.name")
            meths = []
            while r3.has_next():
                meths.append(r3.get_next()[0])
            meth_str = f" → {', '.join(meths[:8])}" if meths else ""
            lines.append(f"  - `{cname}{impl}`{meth_str}")

        # Key functions (not in classes)
        r2 = conn.execute(f"MATCH (f:Function) WHERE f.file STARTS WITH '{prefix}' RETURN f.name, f.file LIMIT 15")
        funcs = []
        while r2.has_next():
            funcs.append(r2.get_next())
        if funcs:
            lines.append(f"- Functions ({len(funcs)}):")
            for fname, ffile in funcs:
                lines.append(f"  - `{fname}` ({ffile})")

        # Cross-service calls
        r2 = conn.execute(
            f"MATCH (a:Function)-[:CALLS]->(b:Function) "
            f"WHERE a.file STARTS WITH '{prefix}' AND NOT b.file STARTS WITH '{prefix}' "
            f"RETURN DISTINCT b.name, b.file LIMIT 10"
        )
        ext_calls = []
        while r2.has_next():
            ext_calls.append(r2.get_next())
        if ext_calls:
            lines.append("- Calls external:")
            for fname, ffile in ext_calls:
                lines.append(f"  - `{fname}` ({ffile})")

        return "\n".join(lines)

    # Try as class
    r = conn.execute(f"MATCH (c:Class) WHERE c.name = '{symbol}' RETURN c.id, c.name, c.file, c.implements")
    if r.has_next():
        row = r.get_next()
        lines.append(f"# Class: {row[1]}")
        lines.append(f"- File: `{row[2]}`")
        if row[3]:
            lines.append(f"- Implements: {row[3]}")
        # Methods
        r2 = conn.execute(f"MATCH (c:Class {{name: '{symbol}'}})-[:HAS_METHOD]->(m:Method) RETURN m.name, m.signature")
        methods = []
        while r2.has_next():
            mrow = r2.get_next()
            methods.append(mrow[1] or mrow[0])
        if methods:
            lines.append(f"- Methods ({len(methods)}):")
            for m in methods[:20]:
                lines.append(f"  - `{m}`")
        return "\n".join(lines)

    # Try as function
    r = conn.execute(f"MATCH (f:Function) WHERE f.name = '{symbol}' RETURN f.id, f.name, f.file, f.signature")
    if r.has_next():
        row = r.get_next()
        lines.append(f"# Function: {row[1]}")
        lines.append(f"- File: `{row[2]}`")
        lines.append(f"- Signature: `{row[3] or row[1]}`")
        # Callers
        r2 = conn.execute(f"MATCH (caller:Function)-[:CALLS]->(f:Function {{name: '{symbol}'}}) RETURN caller.name, caller.file LIMIT 10")
        callers = []
        while r2.has_next():
            crow = r2.get_next()
            callers.append(f"{crow[0]} ({crow[1]})")
        if callers:
            lines.append(f"- Called by: {', '.join(callers)}")
        return "\n".join(lines)

    # Try as folder prefix (service without Project node)
    r = conn.execute(f"MATCH (c:Class) WHERE c.file STARTS WITH '{symbol}/' RETURN c.name, c.file, c.implements LIMIT 30")
    folder_classes = []
    while r.has_next():
        folder_classes.append(r.get_next())
    if folder_classes:
        lines.append(f"# Folder: {symbol}/ ({len(folder_classes)} classes)")
        for cname, cfile, cimpl in folder_classes:
            impl = f" : {cimpl}" if cimpl else ""
            r2 = conn.execute(f"MATCH (c:Class {{name: '{cname}', file: '{cfile}'}})-[:HAS_METHOD]->(m:Method) RETURN m.name")
            meths = []
            while r2.has_next():
                meths.append(r2.get_next()[0])
            meth_str = f" → {', '.join(meths[:8])}" if meths else ""
            lines.append(f"  - `{cname}{impl}`{meth_str}")
        return "\n".join(lines)

    return f"Symbol '{symbol}' not found in graph."


@tool("mnemo_map", "Regenerate the repo map and return the compact tree.")
def _map(root: Path, args: dict) -> str:
    from ..init import _generate_legacy_files
    _generate_legacy_files(root)
    tree = root / ".mnemo" / "tree.md"
    if tree.exists():
        return tree.read_text(encoding="utf-8")
    return "No graph database. Run `mnemo init` first."
