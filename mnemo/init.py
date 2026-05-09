"""Initialize .mnemo in a repository and configure MCP clients."""

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
from .repo_map import save_repo_map


MNEMO_RULE_HEADER = """\
You have access to Mnemo - a persistent memory system for this project.
All project context, decisions, and chat history is below. Use it to answer questions without re-reading files.

AT THE START OF EVERY CHAT:
- Call `mnemo_recall` to get the latest context. The embedded context below may be stale.

SAVING MEMORY:
- Call `mnemo_remember` when the conversation has produced something worth preserving for future chats: a decision, a bug fix, a preference, a TODO, or important context.
- Call `mnemo_remember` when the context window is getting long to summarize the conversation so far.
- Call `mnemo_remember` when the user explicitly asks to remember something.
- Do not call it after every response. Save only meaningful information.

AVAILABLE TOOLS:
- `mnemo_lookup` - get method-level details for a file or folder
- `mnemo_similar` - find similar implementations to follow as patterns
- `mnemo_intelligence` - architecture graph, patterns, dependencies
- `mnemo_discover_apis` - discover all API endpoints
- `mnemo_search_api` - search for a specific endpoint
- `mnemo_knowledge` - search team knowledge base
- `mnemo_decide` - record a decision
- `mnemo_context` - save project metadata
- `mnemo_map` - refresh code map after changes

---

"""


def _build_rule_with_context(repo_root: Path) -> str:
    """Build a client context file with embedded Mnemo context."""
    from .memory import recall

    context = recall(repo_root)
    return MNEMO_RULE_HEADER + context if context else MNEMO_RULE_HEADER


def _install_context_file(repo_root: Path, target: ClientTarget) -> Path | None:
    """Install or refresh the repo-local context file for a client."""
    path = context_path(repo_root, target)
    if path is None:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_build_rule_with_context(repo_root), encoding="utf-8")
    return path


def refresh_context_files(repo_root: Path) -> None:
    """Refresh all known Mnemo client context files that already exist."""
    for target in CLIENTS.values():
        path = context_path(repo_root, target)
        if path and path.exists():
            path.write_text(_build_rule_with_context(repo_root), encoding="utf-8")


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
    targets = resolve_clients(client)
    base = mnemo_path(repo_root)
    base.mkdir(exist_ok=True)

    save_repo_map(repo_root)

    from .knowledge import init_knowledge

    init_knowledge(repo_root)

    from .intelligence import detect_patterns

    patterns = detect_patterns(repo_root)
    context_data = {
        "repo_root": str(repo_root),
        "initialized": True,
    }
    if patterns:
        context_data["patterns"] = patterns
    save_context(repo_root, context_data)

    _ensure_gitignore(repo_root)

    context_results: list[tuple[ClientTarget, Path | None]] = []
    config_results: list[tuple[ClientTarget, bool]] = []
    for target in targets:
        context_results.append((target, _install_context_file(repo_root, target)))
        config_results.append((target, setup_mcp_config(target)))

    lines = [
        "Mnemo initialized",
        f"- .mnemo/ created at {base}",
        "- Repo map generated",
        "- Knowledge base directory ready",
    ]

    for target, path in context_results:
        if path:
            rel = path.relative_to(repo_root)
            lines.append(f"- {target.display_name} {target.context_label} installed at {rel}")

    for target, changed in config_results:
        if target.mcp_config_path:
            state = "configured" if changed else "already configured"
            lines.append(f"- {target.display_name} MCP {state} at {target.mcp_config_path}")

    if client == DEFAULT_CLIENT:
        lines.append("")
        lines.append("Amazon Q will now recall project memory at the start of every new chat.")
    else:
        client_names = ", ".join(target.display_name for target in targets)
        lines.append("")
        lines.append(f"{client_names} will now have access to Mnemo project memory.")

    return "\n".join(lines)
