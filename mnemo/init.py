"""Initialize .mnemo in a repository and configure MCP clients."""

from __future__ import annotations

from pathlib import Path

from .clients import (
    CLIENTS,
    DEFAULT_CLIENT,
    ClientTarget,
    context_path,
    resolve_clients,
    setup_mcp_config,
)
from .config import mnemo_path
from .memory import save_context
from .prompts import (
    build_rule_with_context,
)


def _install_context_file(repo_root: Path, target: ClientTarget) -> Path | None:
    """Install or refresh the repo-local context file for a client."""

    path = context_path(repo_root, target)
    if path is None:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_rule_with_context(repo_root, target), encoding="utf-8")
    return path


def refresh_context_files(repo_root: Path) -> None:
    """Refresh all known Mnemo client context files that already exist."""
    for target in CLIENTS.values():
        path = context_path(repo_root, target)
        if path and path.exists():
            path.write_text(build_rule_with_context(repo_root, target), encoding="utf-8")


def _generate_legacy_files(repo_root: Path) -> None:
    """Generate summary.md and tree.md from LadybugDB for backward compat (recall, context files)."""
    import json
    from .engine.db import open_db, get_db_path
    if not get_db_path(repo_root).exists():
        return

    base = mnemo_path(repo_root)
    _, conn = open_db(repo_root)
    lines = []
    total_nodes = 0
    total_edges = 0

    try:
        r = conn.execute("MATCH (n) RETURN count(n)")
        total_nodes = r.get_next()[0]
        r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
        total_edges = r.get_next()[0]

        # Files by service
        r = conn.execute("MATCH (f:File) RETURN f.path")
        files_by_svc: dict[str, int] = {}
        while r.has_next():
            path = r.get_next()[0]
            svc = path.split("/")[0] if "/" in path else "."
            files_by_svc[svc] = files_by_svc.get(svc, 0) + 1

        # Classes by service
        r = conn.execute("MATCH (c:Class) RETURN c.name, c.file")
        classes_by_svc: dict[str, list[str]] = {}
        while r.has_next():
            row = r.get_next()
            svc = row[1].split("/")[0] if "/" in row[1] else "."
            classes_by_svc.setdefault(svc, []).append(row[0])

        # Communities
        r = conn.execute("MATCH (c:Community) RETURN c.name LIMIT 5")
        hubs = []
        while r.has_next():
            hubs.append(r.get_next()[0])

        # Build tree
        lines.append("# Repo Map")
        lines.append("(use mnemo_lookup for method-level details, mnemo_query for relationships)")
        lines.append("")
        lines.append(f"Knowledge Graph: {total_nodes} nodes, {total_edges} edges")
        if hubs:
            lines.append(f"Key clusters: {', '.join(hubs)}")
        lines.append("")

        for svc in sorted(files_by_svc.keys()):
            fc = files_by_svc[svc]
            classes = classes_by_svc.get(svc, [])
            lines.append(f"{svc}/ ({fc} files)")
            if classes:
                lines.append(f"  Classes: {', '.join(sorted(set(classes)))}")

    except RuntimeError:
        lines = ["(graph not available — run mnemo init)"]

    tree_content = "\n".join(line for line in lines if line is not None)
    (base / "tree.md").write_text(tree_content, encoding="utf-8")
    (base / "summary.md").write_text(tree_content, encoding="utf-8")
    (base / "graph_meta.json").write_text(json.dumps({"nodes": total_nodes, "edges": total_edges}), encoding="utf-8")


def _ensure_gitignore(repo_root: Path) -> None:
    """Ensure local Mnemo data is ignored by git."""
    gitignore = repo_root / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
        if ".mnemo" not in content:
            gitignore.write_text(content.rstrip() + "\n.mnemo/\n", encoding="utf-8")
    else:
        gitignore.write_text(".mnemo/\n", encoding="utf-8")


def init(repo_root: Path, client: str = DEFAULT_CLIENT) -> str:
    """Create .mnemo/, generate repo map, install context files, and configure MCP."""
    import os
    os.environ["MNEMO_AUTO_INSTALL"] = "1"

    targets = resolve_clients(client)
    base = mnemo_path(repo_root)
    base.mkdir(exist_ok=True)

    # Run the new v2 engine pipeline (LadybugDB + tree-sitter + scope + communities)
    print("⏳ Indexing repository...", flush=True)
    from .engine.pipeline import run_pipeline
    stats = run_pipeline(repo_root, force=False)

    # Generate legacy files (summary.md, tree.md) from LadybugDB for recall/context
    _generate_legacy_files(repo_root)

    # Generate default rules.yaml if not exists
    from .drift import _init_rules
    _init_rules(repo_root)

    from .knowledge import init_knowledge
    init_knowledge(repo_root)

    context_data = {
        "repo_root": str(repo_root),
        "initialized": True,
    }
    if stats.nodes_created:
        context_data["engine_stats"] = {
            "files": stats.files_scanned,
            "nodes": stats.nodes_created,
            "edges": stats.edges_created,
            "total_ms": stats.total_ms,
        }

    # Auto-detect project info from graph
    try:
        from .engine.db import open_db, get_db_path
        if get_db_path(repo_root).exists():
            _, conn = open_db(repo_root)
            # Languages
            r = conn.execute("MATCH (f:File) RETURN f.language, count(f) ORDER BY count(f) DESC LIMIT 5")
            langs = []
            while r.has_next():
                row = r.get_next()
                langs.append(f"{row[0]} ({row[1]})")
            if langs:
                context_data["languages"] = ", ".join(langs)
            # Projects/services
            r = conn.execute("MATCH (p:Project) RETURN p.name, p.language LIMIT 10")
            projects = []
            while r.has_next():
                row = r.get_next()
                projects.append(f"{row[0]} ({row[1]})")
            if projects:
                context_data["services"] = ", ".join(projects)
            # Key classes
            r = conn.execute("MATCH (c:Class) RETURN c.name LIMIT 20")
            classes = []
            while r.has_next():
                classes.append(r.get_next()[0])
            if classes:
                context_data["key_classes"] = ", ".join(classes[:15])
    except Exception:
        pass

    save_context(repo_root, context_data)

    _ensure_gitignore(repo_root)

    context_results: list[tuple[ClientTarget, Path | None]] = []
    config_results: list[tuple[ClientTarget, bool]] = []
    for target in targets:
        context_results.append((target, _install_context_file(repo_root, target)))
        config_results.append((target, setup_mcp_config(target, repo_root=repo_root)))

    lines = [
        "Mnemo initialized",
        f"- .mnemo/ created at {base}",
    ]
    if stats.nodes_created:
        lines.append(f"- Code graph: {stats.nodes_created} nodes, {stats.edges_created} edges ({stats.total_ms}ms)")
    else:
        lines.append(f"- Code graph: up to date ({stats.total_ms}ms)")
    lines.append("- Knowledge base directory ready")

    for target, path in context_results:
        if path:
            rel = path.relative_to(repo_root)
            lines.append(f"- {target.display_name} {target.context_label} installed at {rel}")

    for target, changed in config_results:
        if target.local_mcp_config or target.mcp_config_path:
            state = "configured" if changed else "already configured"
            display_path = target.local_mcp_config or target.mcp_config_path
            lines.append(f"- {target.display_name} MCP {state} at {display_path}")

    # Auto-install hooks + skills for clients that support them
    print("⏳ Installing hooks and agent config...", flush=True)
    from .hooks import install_hooks
    for target in targets:
        if target.key == "kiro":
            result = install_hooks(repo_root, "kiro")
            lines.append(f"- {result}")
        elif target.key == "claude-code":
            result = install_hooks(repo_root, "claude-code")
            lines.append(f"- {result}")

    if client == DEFAULT_CLIENT:
        lines.append("")
        lines.append("Amazon Q will now recall project memory at the start of every new chat.")
    else:
        client_names = ", ".join(target.display_name for target in targets)
        lines.append("")
        lines.append(f"{client_names} will now have access to Mnemo project memory.")

    return "\n".join(lines)
