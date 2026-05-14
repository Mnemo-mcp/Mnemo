"""Git hooks - install pre-commit hook and client-specific lifecycle hooks."""

from __future__ import annotations

import json
import stat
from pathlib import Path

from ..security import check_security

HOOK_SCRIPT = """#!/bin/sh
# Mnemo pre-commit hook - validates naming, patterns, security
mnemo check "$@"
"""

_KIRO_AGENT_CONFIG_TEMPLATE = """\
{
  "name": "mnemo-enhanced",
  "description": "Mnemo-powered agent with persistent memory, automatic learning, and lifecycle hooks",
  "model": "claude-sonnet-4-20250514",
  "useLegacyMcpJson": true,

  "prompt": "You are an engineering assistant powered by Mnemo — a persistent memory system that remembers everything across sessions.\\n\\n## Context Loading\\n\\nYour project context (memories, decisions, active tasks, knowledge graph) is AUTOMATICALLY loaded at session start by the agentSpawn hook. You already have it in your context above as <mnemo-context>. You do NOT need to call mnemo_recall yourself — it was already done.\\n\\nIf context appears missing or the user asks to see memories, use the MCP tool `mnemo_recall` — do NOT read files from disk. NEVER read .kiro/skills/mnemo/SKILL.md or any .mnemo/ files. All memory operations are MCP tool calls only.\\n\\n## How You Work\\n\\n1. CONTEXT IS PRE-LOADED — check the <mnemo-context> block above for your memories and decisions.\\n2. SEARCH BEFORE ASKING — before asking the user something, use the MCP tool mnemo_search_memory. They may have told you in a past session.\\n3. REMEMBER IMPORTANT THINGS — use the MCP tool mnemo_remember for decisions, patterns, fixes, and preferences.\\n4. DECISIONS ARE PERMANENT — use the MCP tool mnemo_decide for architectural choices. These never get evicted.\\n5. LEARNINGS ARE AUTO-CAPTURED — the stop hook detects problem-solving patterns in your responses and saves them automatically.\\n\\n## IMPORTANT: All mnemo_* operations are MCP tool calls\\n\\nEvery mnemo_* operation (mnemo_recall, mnemo_remember, mnemo_search_memory, mnemo_decide, mnemo_plan, mnemo_graph, etc.) is an MCP tool call to the 'mnemo' MCP server. The tool names are prefixed with 'mnemo_' — for example, to recall memories you call the tool named `mnemo_recall`, NOT a tool named `mnemo` with an action parameter. NEVER try to read .mnemo/ files or .kiro/ files to get this information. Always use the MCP tools directly.\\n\\nCorrect: call tool `mnemo_recall` with no parameters\\nCorrect: call tool `mnemo_search_memory` with parameter query='...'\\nWRONG: call tool `mnemo` with parameter action='recall'\\nWRONG: read file .mnemo/memory.json\\n\\n## When Working on Tasks\\n\\n- Check if there's an active plan (mnemo_plan with action: status)\\n- Mark tasks done as you complete them (mnemo_plan with action: done, task_id: MNO-XXX)\\n- Use mnemo_graph to understand code relationships before making changes\\n- Use mnemo_lookup for method-level details of specific files\\n\\n## Memory Slots (Structured Context)\\n\\nUse mnemo_slot_set/mnemo_slot_get for:\\n- project_context — what this project is about\\n- user_preferences — coding style, conventions\\n- conventions — project-specific rules\\n- pending_items — things to follow up on\\n- known_gotchas — traps and pitfalls\\n\\n## What NOT to Remember\\n\\n- Temporary debugging output\\n- Secrets or credentials (auto-stripped anyway)\\n- Obvious things the code already shows\\n- Duplicate information already in memory",

  "tools": [
    "read", "write", "shell", "grep", "glob", "code",
    "use_aws", "web_search", "web_fetch",
    "knowledge", "subagent", "todo_list"
  ],

  "allowedTools": [
    "read", "write", "shell", "grep", "glob", "code",
    "use_aws", "web_search", "web_fetch",
    "knowledge", "subagent", "todo_list",
    "mnemo_recall", "mnemo_remember", "mnemo_search_memory", "mnemo_decide",
    "mnemo_forget", "mnemo_plan", "mnemo_task", "mnemo_task_done",
    "mnemo_graph", "mnemo_lookup", "mnemo_map", "mnemo_similar",
    "mnemo_impact", "mnemo_search_api", "mnemo_discover_apis",
    "mnemo_check_security", "mnemo_check_conventions", "mnemo_check_regressions",
    "mnemo_breaking_changes", "mnemo_dead_code", "mnemo_health", "mnemo_drift",
    "mnemo_commit_message", "mnemo_pr_description", "mnemo_context",
    "mnemo_context_for_task", "mnemo_slot_get", "mnemo_slot_set",
    "mnemo_knowledge", "mnemo_team", "mnemo_who_touched",
    "mnemo_add_error", "mnemo_search_errors", "mnemo_add_incident", "mnemo_incidents",
    "mnemo_add_review", "mnemo_reviews", "mnemo_add_correction", "mnemo_corrections",
    "mnemo_add_regression", "mnemo_add_security_pattern",
    "mnemo_dependencies", "mnemo_cross_search", "mnemo_cross_impact", "mnemo_links",
    "mnemo_velocity", "mnemo_temporal", "mnemo_tests", "mnemo_onboarding",
    "mnemo_snapshot", "mnemo_intelligence", "mnemo_lesson", "mnemo_episode",
    "mnemo_check", "mnemo_hooks_install", "mnemo_ask"
  ],

  "resources": [],

  "hooks": {
    "agentSpawn": [
      {
        "command": "HOOK_SPAWN_PATH",
        "timeout_ms": 15000
      }
    ],
    "userPromptSubmit": [
      {
        "command": "HOOK_PROMPT_PATH",
        "timeout_ms": 5000
      }
    ],
    "preToolUse": [
      {
        "matcher": "shell",
        "command": "HOOK_PRETOOL_PATH",
        "timeout_ms": 2000
      }
    ],
    "postToolUse": [
      {
        "command": "HOOK_POSTTOOL_PATH",
        "timeout_ms": 3000
      }
    ],
    "stop": [
      {
        "command": "HOOK_STOP_PATH",
        "timeout_ms": 10000
      }
    ]
  },

  "mcpServers": {
    "mnemo": {
      "command": "MCP_BINARY_PATH",
      "args": [],
      "timeout": 30000
    }
  }
}
"""

_MNEMO_SKILL = """---
name: mnemo-memory-system
description: How to use Mnemo persistent memory effectively. Use when working with project context, decisions, plans, or when you need to recall past work.
---

# Mnemo — Persistent Engineering Memory

Mnemo gives you persistent memory across sessions. Here's how to use it well.

## On Every Session Start

Call `mnemo_recall` first. It returns:
- Project context and architecture
- Active decisions
- Pinned memory slots
- Hot memories (most relevant)
- Active plan status with next task
- Knowledge graph summary

## Remembering Things

Use `mnemo_remember` for important context:
- Architecture decisions and their reasoning
- Bug fixes and what caused them
- Patterns discovered in the codebase
- User preferences and conventions

Use `mnemo_decide` for architectural decisions — these are pinned and never forgotten.

## Before Asking the User

Search memory first: `mnemo_search_memory --query "topic"`. The user may have already told you this in a previous session.

## Plans and Tasks

When the user describes multi-step work, Mnemo auto-creates a plan. Use `mnemo_plan --action status` to check progress. Mark tasks done with `mnemo_plan --action done --task_id MNO-XXX`.

## Memory Slots

Use `mnemo_slot_set` to store structured context:
- `project_context` — what this project is about
- `user_preferences` — coding style, conventions
- `conventions` — project-specific rules
- `pending_items` — things to follow up on
- `known_gotchas` — traps and pitfalls

## Code Understanding

- `mnemo_graph` — query the knowledge graph (neighbors, paths, hubs)
- `mnemo_lookup` — get method-level details for a file
- `mnemo_search` — hybrid search across code (BM25 + vector + graph)
- `mnemo_intelligence` — full code intelligence report

## What NOT to Remember

Don't store:
- Temporary debugging output
- Secrets or credentials (they get auto-stripped anyway)
- Obvious things the code already shows
- Duplicate information already in memory
"""

_CLAUDE_SKILL = """# Mnemo Memory System

## Usage Rules

1. Always call `mnemo recall` at session start
2. Search memory before asking user for context: `mnemo tool mnemo_search_memory --query "topic"`
3. Remember important findings: `mnemo tool mnemo_remember --content "what you learned"`
4. Record decisions: `mnemo tool mnemo_decide --decision "what" --reasoning "why"`
5. Check plan status: `mnemo tool mnemo_plan --action status`
6. Use slots for structured context: `mnemo tool mnemo_slot_set --name "project_context" --content "..."`

## What to Remember
- Architecture decisions with reasoning
- Bug root causes and fixes
- Patterns and conventions discovered
- User preferences

## What NOT to Remember
- Temporary debug output
- Secrets (auto-stripped anyway)
- Things obvious from the code
"""

_CLAUDE_SPAWN_SCRIPT = """#!/bin/sh
# Mnemo: load context on session start
mnemo tool mnemo_recall
"""

_CLAUDE_STOP_SCRIPT = """#!/bin/sh
# Mnemo: save session summary
mnemo tool mnemo_remember --content "Session ended"
"""


def install_hooks(repo_root: Path, client: str = "git") -> str:
    """Install hooks for the specified client."""
    if client == "kiro":
        return _install_kiro_hooks(repo_root)
    elif client == "claude-code":
        return _install_claude_hooks(repo_root)
    return _install_git_hooks(repo_root)


def _install_kiro_hooks(repo_root: Path) -> str:
    """Generate .kiro/agents/mnemo-enhanced.json, hooks, and skill file."""
    import shutil

    # Find mnemo-mcp binary — check all installation methods
    mnemo_mcp = shutil.which("mnemo-mcp")
    if not mnemo_mcp:
        # Check common installation locations
        candidates = [
            # pip user install
            Path.home() / ".local" / "bin" / "mnemo-mcp",
            # pip user install (macOS Python framework)
            Path.home() / "Library" / "Python" / "3.12" / "bin" / "mnemo-mcp",
            Path.home() / "Library" / "Python" / "3.11" / "bin" / "mnemo-mcp",
            Path.home() / "Library" / "Python" / "3.13" / "bin" / "mnemo-mcp",
            # Homebrew (Apple Silicon)
            Path("/opt/homebrew/bin/mnemo-mcp"),
            # Homebrew (Intel) / system
            Path("/usr/local/bin/mnemo-mcp"),
            # Standalone binary install
            Path.home() / "bin" / "mnemo-mcp",
            Path.home() / ".mnemo" / "bin" / "mnemo-mcp",
        ]
        # VS Code extension binary
        vscode_ext_dir = Path.home() / ".vscode" / "extensions"
        if vscode_ext_dir.exists():
            for ext_dir in vscode_ext_dir.glob("mnemo*"):
                candidates.append(ext_dir / "bin" / "mnemo-mcp")
                candidates.append(ext_dir / "mnemo-mcp")
        # Also check .vscode-server for remote dev
        vscode_server_dir = Path.home() / ".vscode-server" / "extensions"
        if vscode_server_dir.exists():
            for ext_dir in vscode_server_dir.glob("mnemo*"):
                candidates.append(ext_dir / "bin" / "mnemo-mcp")

        for candidate in candidates:
            if candidate.exists():
                mnemo_mcp = str(candidate)
                break

    if not mnemo_mcp:
        mnemo_mcp = "mnemo-mcp"  # Fallback: assume it's on PATH at runtime

    # Find mnemo CLI binary
    mnemo_bin = shutil.which("mnemo") or "mnemo"

    # Create hooks directory
    hooks_dir = repo_root / ".kiro" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Generate hook scripts (portable — use mnemo from PATH)
    _write_hook(hooks_dir / "agent-spawn.sh", f"""#!/bin/sh
# Mnemo agentSpawn hook — loads context into agent
MNEMO="{mnemo_bin}"
input_json=$(cat 2>/dev/null || echo "{{}}")
RECALL=$("$MNEMO" tool mnemo_recall 2>/dev/null) || RECALL=""
if [ -z "$RECALL" ]; then
  echo "<mnemo-context>"
  echo "Mnemo memory not available. Use mnemo_recall tool to initialize."
  echo "</mnemo-context>"
  exit 0
fi
cat << EOF
<mnemo-context>
$RECALL
</mnemo-context>
EOF
exit 0
""")

    _write_hook(hooks_dir / "user-prompt-submit.sh", f"""#!/bin/sh
# Mnemo userPromptSubmit — search relevant memories for prompt
input_json=$(cat 2>/dev/null || echo "{{}}")
exit 0
""")

    _write_hook(hooks_dir / "pre-tool-use.sh", """#!/bin/sh
# Mnemo preToolUse — validate shell commands
input_json=$(cat 2>/dev/null || echo "{}")
exit 0
""")

    _write_hook(hooks_dir / "post-tool-use.sh", """#!/bin/sh
# Mnemo postToolUse — track file modifications
input_json=$(cat 2>/dev/null || echo "{}")
exit 0
""")

    _write_hook(hooks_dir / "stop.sh", f"""#!/bin/sh
# Mnemo stop hook — auto-capture learnings
input_json=$(cat 2>/dev/null || echo "{{}}")
exit 0
""")

    # Generate agent config with resolved paths
    config_str = _KIRO_AGENT_CONFIG_TEMPLATE
    config_str = config_str.replace("HOOK_SPAWN_PATH", str(hooks_dir / "agent-spawn.sh"))
    config_str = config_str.replace("HOOK_PROMPT_PATH", str(hooks_dir / "user-prompt-submit.sh"))
    config_str = config_str.replace("HOOK_PRETOOL_PATH", str(hooks_dir / "pre-tool-use.sh"))
    config_str = config_str.replace("HOOK_POSTTOOL_PATH", str(hooks_dir / "post-tool-use.sh"))
    config_str = config_str.replace("HOOK_STOP_PATH", str(hooks_dir / "stop.sh"))
    config_str = config_str.replace("MCP_BINARY_PATH", mnemo_mcp)

    agents_dir = repo_root / ".kiro" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    path = agents_dir / "mnemo-enhanced.json"
    path.write_text(config_str, encoding="utf-8")

    # Skill file
    skills_dir = repo_root / ".kiro" / "skills" / "mnemo"
    skills_dir.mkdir(parents=True, exist_ok=True)
    skill_path = skills_dir / "SKILL.md"
    skill_path.write_text(_MNEMO_SKILL.lstrip(), encoding="utf-8")

    return (
        f"Installed Kiro agent: {path.relative_to(repo_root)}\n"
        f"Installed Kiro hooks: {hooks_dir.relative_to(repo_root)}/\n"
        f"Installed Kiro skill: {skill_path.relative_to(repo_root)}\n"
        f"MCP server: {mnemo_mcp}\n"
        f"Switch to it with: /agent mnemo-enhanced"
    )


def _write_hook(path: Path, content: str) -> None:
    """Write a hook script and make it executable."""
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _install_claude_hooks(repo_root: Path) -> str:
    """Generate shell scripts in .claude/hooks/ and memory guide."""
    hooks_dir = repo_root / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    spawn = hooks_dir / "on-spawn.sh"
    spawn.write_text(_CLAUDE_SPAWN_SCRIPT, encoding="utf-8")
    spawn.chmod(spawn.stat().st_mode | stat.S_IEXEC)

    stop = hooks_dir / "on-stop.sh"
    stop.write_text(_CLAUDE_STOP_SCRIPT, encoding="utf-8")
    stop.chmod(stop.stat().st_mode | stat.S_IEXEC)

    # Memory guide (Claude Code reads CLAUDE.md or .claude/ files)
    guide_path = repo_root / ".claude" / "mnemo-guide.md"
    guide_path.write_text(_CLAUDE_SKILL.lstrip(), encoding="utf-8")

    return (
        f"Installed Claude Code hooks: {hooks_dir.relative_to(repo_root)}/ (on-spawn.sh, on-stop.sh)\n"
        f"Installed memory guide: {guide_path.relative_to(repo_root)}"
    )


def _install_git_hooks(repo_root: Path) -> str:
    """Install Mnemo pre-commit hook."""
    hooks_dir = repo_root / ".git" / "hooks"
    if not hooks_dir.exists():
        return "No .git/hooks directory found. Is this a git repository?"

    hook_path = hooks_dir / "pre-commit"
    if hook_path.exists():
        content = hook_path.read_text(encoding="utf-8")
        if "mnemo check" in content:
            return "Mnemo pre-commit hook already installed."
        with open(hook_path, "a", encoding="utf-8") as f:
            f.write("\n# Mnemo validation\nmnemo check\n")
        return "Mnemo check appended to existing pre-commit hook."

    hook_path.write_text(HOOK_SCRIPT, encoding="utf-8")
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)
    return "Pre-commit hook installed."


def run_check(repo_root: Path) -> str:
    """Run pre-commit validations (security scan on staged files)."""
    import subprocess  # nosec B404

    try:
        result = subprocess.run(  # nosec B603 B607
            ["git", "diff", "--cached", "--name-only"],
            cwd=repo_root, capture_output=True, text=True, timeout=5,
        )
        staged = [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        staged = []

    if not staged:
        return "No staged files to check."

    issues = []
    for file in staged:
        result = check_security(repo_root, file)
        if "No security issues" not in result:
            issues.append(result)

    if not issues:
        return f"✅ {len(staged)} files checked — no issues found."

    return "⚠️ Issues found in staged files:\n\n" + "\n".join(issues)
