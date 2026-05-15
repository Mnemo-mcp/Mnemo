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
