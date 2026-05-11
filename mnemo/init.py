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

ANSWERING QUESTIONS:
- If the recalled memory already contains the answer, USE IT DIRECTLY. Do not re-read files or re-run lookups for information already in memory.
- Only call `mnemo_lookup` or read files when memory does not have enough detail to answer.

SAVING MEMORY:
- Call `mnemo_remember` AFTER any of these happen in the conversation:
  - You made a code change that affects behavior (theme change, config change, new feature, refactor)
  - A bug was found and fixed
  - A design or architecture decision was made
  - The user stated a preference or convention
  - A TODO or follow-up was identified
  - You learned something non-obvious about the codebase
- Call `mnemo_remember` when the context window is getting long to summarize progress so far.
- Call `mnemo_remember` when the user explicitly asks to remember something.
- Do NOT save trivial things like "read a file" or "answered a question with no new insight".
- When in doubt, SAVE. It is better to remember too much than to forget something useful.
- RULE: If you called `mnemo_lookup`, `mnemo_similar`, or `mnemo_who_touched` AND produced a summary or analysis from the results, you MUST call `mnemo_remember` with a concise summary before ending your response.

WHEN TO USE WHAT:
- Understanding code structure → `mnemo_lookup` or `mnemo_graph action=neighbors`
- Finding patterns/similar code → `mnemo_similar` or `mnemo_graph action=find`
- Impact of a change → `mnemo_graph action=traverse direction=incoming` or `mnemo_cross_impact`
- Code relationships/path between entities → `mnemo_graph action=path`
- Code health/quality → `mnemo_health`, `mnemo_dead_code`, `mnemo_check_security`
- Team/ownership → `mnemo_team`, `mnemo_who_touched`
- History/context → `mnemo_search_memory`, `mnemo_search_errors`, `mnemo_incidents`
- APIs → `mnemo_discover_apis`, `mnemo_search_api`
- Knowledge base → `mnemo_knowledge`
- Record decisions → `mnemo_decide`
- Refresh after code changes → `mnemo_map`
- Cross-repo search → `mnemo_cross_search`
- Cross-repo impact → `mnemo_cross_impact`

PLAN MODE:
- When the user asks to plan a feature, break work into tasks, or track progress → use `mnemo_plan`
- `mnemo_plan action=create` — create a new plan with tasks
- `mnemo_plan action=done` — mark a task complete (with summary)
- `mnemo_plan action=status` — show current plan progress
- After completing any work that matches an open plan item, AUTOMATICALLY call `mnemo_plan action=done`
- When starting a new chat, if plan status shows open tasks, mention what's next

CROSS-REPO AWARENESS:
- This repo may have linked sibling repos. Use `mnemo_links` to see them.
- ALWAYS call `mnemo_cross_search` BEFORE using grep or reading files when:
  - The user asks about code that does not exist in this repo
  - The user mentions a service, project, or module name that is not a folder in this repo
  - `mnemo_lookup` or `mnemo_similar` returned no results
- If the user asks "what breaks if I change X", use `mnemo_cross_impact` for full cross-repo analysis.
- NEVER fall back to grep for code in other repos. Use `mnemo_cross_search` instead.

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
    import os
    os.environ["MNEMO_AUTO_INSTALL"] = "1"

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
