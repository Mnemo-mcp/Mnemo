"""Initialize .mnemo in a repository and configure Amazon Q MCP."""

import json
from pathlib import Path

from .config import mnemo_path
from .repo_map import save_repo_map
from .memory import save_context

MCP_CONFIG_PATH = Path.home() / ".aws" / "amazonq" / "mcp.json"

MNEMO_RULE_HEADER = """\
You have access to Mnemo — a persistent memory system for this project.
All project context, decisions, and chat history is below. Use it to answer questions without re-reading files.

AT THE START OF EVERY CHAT:
- Call `mnemo_recall` to get the latest context (the embedded context below may be stale).

SAVING MEMORY:
- Call `mnemo_remember` when the conversation has produced something worth preserving for future chats: a decision, a bug fix, a preference, a TODO, or important context.
- Call `mnemo_remember` when the context window is getting long (many back-and-forth exchanges) to summarize the conversation so far.
- Call `mnemo_remember` when the user explicitly asks to remember something.
- Do NOT call it after every single response — only when there is meaningful information to persist.

AVAILABLE TOOLS (use based on your judgement):
- `mnemo_lookup` — get method-level details for a file or folder
- `mnemo_similar` — find similar implementations to follow as patterns
- `mnemo_intelligence` — architecture graph, patterns, dependencies
- `mnemo_discover_apis` — discover all API endpoints
- `mnemo_search_api` — search for a specific endpoint
- `mnemo_knowledge` — search team knowledge base
- `mnemo_decide` — record a decision
- `mnemo_context` — save project metadata
- `mnemo_map` — refresh code map after changes

---

"""


def _build_rule_with_context(repo_root: Path) -> str:
    """Build the rule file with embedded context so Q reads it automatically."""
    from .memory import recall
    context = recall(repo_root)
    return MNEMO_RULE_HEADER + context if context else MNEMO_RULE_HEADER


def _setup_mcp_config():
    """Auto-register mnemo MCP server in Amazon Q config."""
    MCP_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    config = {}
    if MCP_CONFIG_PATH.exists():
        try:
            config = json.loads(MCP_CONFIG_PATH.read_text())
        except json.JSONDecodeError:
            config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    if "mnemo" not in config["mcpServers"]:
        import shutil
        import sys
        mnemo_bin = shutil.which("mnemo-mcp")
        if not mnemo_bin:
            # Check common user install paths
            candidates = [
                Path(sys.prefix) / "bin" / "mnemo-mcp",  # venv
                Path.home() / ".local" / "bin" / "mnemo-mcp",  # Linux pip --user
                Path.home() / "Library" / "Python" / "3.12" / "bin" / "mnemo-mcp",  # macOS
                Path.home() / "Library" / "Python" / "3.11" / "bin" / "mnemo-mcp",  # macOS
            ]
            for candidate in candidates:
                if candidate.exists():
                    mnemo_bin = str(candidate)
                    break
            else:
                mnemo_bin = "mnemo-mcp"

        config["mcpServers"]["mnemo"] = {
            "command": mnemo_bin,
            "args": [],
            "env": {},
        }
        MCP_CONFIG_PATH.write_text(json.dumps(config, indent=2))
        return True
    return False


def _install_rule(repo_root: Path):
    """Install the auto-recall rule with embedded context into .amazonq/rules/."""
    rules_dir = repo_root / ".amazonq" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    rule_file = rules_dir / "mnemo.md"
    rule_file.write_text(_build_rule_with_context(repo_root))
    return rule_file


def init(repo_root: Path) -> str:
    """Create .mnemo/ folder, generate repo map, install rule, configure MCP."""
    base = mnemo_path(repo_root)
    base.mkdir(exist_ok=True)

    # Generate initial repo map
    save_repo_map(repo_root)

    # Create knowledge base directory
    from .knowledge import init_knowledge
    init_knowledge(repo_root)

    # Bootstrap context with detected intelligence
    from .intelligence import detect_patterns, detect_dependencies
    patterns = detect_patterns(repo_root)
    context_data = {
        "repo_root": str(repo_root),
        "initialized": True,
    }
    if patterns:
        context_data["patterns"] = patterns
    save_context(repo_root, context_data)

    # Add .mnemo to .gitignore
    gitignore = repo_root / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text()
        if ".mnemo" not in content:
            gitignore.write_text(content.rstrip() + "\n.mnemo/\n")
    else:
        gitignore.write_text(".mnemo/\n")

    # Install auto-recall rule for Amazon Q
    _install_rule(repo_root)

    # Auto-configure Amazon Q MCP
    mcp_added = _setup_mcp_config()

    msg = """
         ╭──────────────────╮
         │  Mnemo Started!  │
         ╰───────┬──────────╯
                 │
            ><(((º>
    """
    msg += f"\n✓ Mnemo initialized\n"
    msg += f"  • .mnemo/ created at {base}\n"
    msg += f"  • Repo map generated (full code context)\n"
    msg += f"  • Auto-recall rule installed at .amazonq/rules/mnemo.md\n"
    if mcp_added:
        msg += f"  • Amazon Q MCP configured at {MCP_CONFIG_PATH}\n"
    else:
        msg += f"  • Amazon Q MCP already configured\n"
    msg += "\nAmazon Q will now recall project memory at the start of every new chat."
    return msg
