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
  "useLegacyMcpJson": true,

  "prompt": "You are an engineering assistant powered by Mnemo — a persistent memory system that remembers everything across sessions.\\n\\n## Context Loading\\n\\nYour project context (memories, decisions, active tasks, knowledge graph) is AUTOMATICALLY loaded at session start by the agentSpawn hook. You already have it in your context above as <mnemo-context>. You do NOT need to call mnemo_recall yourself — it was already done.\\n\\nIf context appears missing or the user asks to see memories, use the MCP tool `mnemo_recall` — do NOT read files from disk. NEVER read .kiro/skills/mnemo/SKILL.md or any .mnemo/ files. All memory operations are MCP tool calls only.\\n\\n## How You Work\\n\\n1. CONTEXT IS PRE-LOADED — check the <mnemo-context> block above for your memories and decisions.\\n2. SEARCH BEFORE ASKING — before asking the user something, use the MCP tool mnemo_search_memory. They may have told you in a past session.\\n3. REMEMBER IMPORTANT THINGS — use the MCP tool mnemo_remember for decisions, patterns, fixes, and preferences.\\n4. DECISIONS ARE PERMANENT — use the MCP tool mnemo_decide for architectural choices. These never get evicted.\\n5. LEARNINGS ARE AUTO-CAPTURED — the stop hook detects problem-solving patterns in your responses and saves them automatically.\\n\\n## IMPORTANT: All mnemo_* operations are MCP tool calls\\n\\nEvery mnemo_* operation (mnemo_recall, mnemo_remember, mnemo_search_memory, mnemo_decide, mnemo_plan, mnemo_graph, etc.) is an MCP tool call to the 'mnemo' MCP server. The tool names are prefixed with 'mnemo_' — for example, to recall memories you call the tool named `mnemo_recall`, NOT a tool named `mnemo` with an action parameter. NEVER try to read .mnemo/ files or .kiro/ files to get this information. Always use the MCP tools directly.\\n\\nCorrect: call tool `mnemo_recall` with no parameters\\nCorrect: call tool `mnemo_search_memory` with parameter query='...'\\nWRONG: call tool `mnemo` with parameter action='recall'\\nWRONG: read file .mnemo/memory.json\\n\\n## When Working on Tasks\\n\\n- Check if there's an active plan (mnemo_plan with action: status)\\n- Mark tasks done as you complete them (mnemo_plan with action: done, task_id: MNO-XXX)\\n- Use mnemo_graph to understand code relationships before making changes\\n- Use mnemo_lookup for method-level details of specific files\\n- Use mnemo_search for hybrid code search (BM25 + vector + graph)\\n\\n## Memory Slots (Structured Context)\\n\\nUse mnemo_slot_set/mnemo_slot_get for:\\n- project_context — what this project is about\\n- user_preferences — coding style, conventions\\n- conventions — project-specific rules\\n- pending_items — things to follow up on\\n- known_gotchas — traps and pitfalls\\n\\n## What NOT to Remember\\n\\n- Temporary debugging output\\n- Secrets or credentials (auto-stripped anyway)\\n- Obvious things the code already shows\\n- Duplicate information already in memory",

  "tools": [
    "read", "write", "shell", "grep", "glob", "code",
    "use_aws", "web_search", "web_fetch",
    "knowledge", "subagent", "todo_list"
  ],

  "allowedTools": [
    "read", "write", "shell", "grep", "glob", "code",
    "use_aws", "web_search", "web_fetch",
    "knowledge", "subagent", "todo_list",
    "mnemo:*"
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
description: Reference for Mnemo MCP tool names and parameters. Use only when you need to look up the exact syntax of a specific mnemo tool.
inclusion: on_demand
---

# Mnemo — Persistent Engineering Memory

Mnemo gives you persistent memory across sessions. Context is automatically loaded at session start via the agentSpawn hook.

## Context Loading (Automatic)

The agentSpawn hook automatically calls `mnemo_recall` and injects the result into your context. You do NOT need to call mnemo_recall yourself — it's already done. If for some reason context appears missing, call the MCP tool `mnemo_recall` (do NOT read files — use the tool).

## What You Should Do

### Search Before Asking
Before asking the user something, search memory via the MCP tool: `mnemo_search_memory`. They may have told you in a past session.

### Record Decisions
Use the MCP tool `mnemo_decide` for architectural choices — these are permanent and never evicted.

### Remember Important Context
Use the MCP tool `mnemo_remember` for:
- Bug fixes and root causes
- Patterns discovered in the codebase
- User preferences and conventions
- Important findings during investigation

### Track Plans
- Check active plans: `mnemo_plan` with action "status"
- Mark tasks done: `mnemo_plan` with action "done" and task_id
- Plans auto-create when you describe multi-step work

### Understand Code
- `mnemo_graph` — query the knowledge graph (neighbors, paths, hubs, why)
- `mnemo_lookup` — method-level details for a file
- `mnemo_search` — hybrid search (BM25 + vector + graph)
- `mnemo_impact` — what breaks if you change something

### Memory Slots
Use `mnemo_slot_set`/`mnemo_slot_get` for structured context:
- `project_context` — what this project is about
- `user_preferences` — coding style, conventions
- `pending_items` — things to follow up on
- `known_gotchas` — traps and pitfalls

## Important: All Mnemo operations are MCP TOOL CALLS

Every `mnemo_*` operation is an MCP tool call to the "mnemo" server. Do NOT try to read files to get this information. Use the tools directly.

## What NOT to Remember
- Temporary debugging output
- Secrets or credentials (auto-stripped anyway)
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
# Mnemo agentSpawn hook — loads full project context into agent
# stdout → injected into agent context | stderr → shown as warning
# Fail-safe: always exits 0

MNEMO="{mnemo_bin}"

# Read STDIN (Kiro sends session JSON) — consume but don't require it
input_json=$(cat 2>/dev/null || echo "{{}}")

# Load recall context
RECALL=$("$MNEMO" tool mnemo_recall 2>/dev/null) || RECALL=""

if [ -z "$RECALL" ]; then
  echo "⚠️ Mnemo recall returned empty — memory may not be initialized." >&2
  echo "<mnemo-context>"
  echo "Mnemo memory not available. Use mnemo_recall tool to initialize."
  echo "</mnemo-context>"
  exit 0
fi

# Get active task context
TASK=$("$MNEMO" tool mnemo_task 2>/dev/null) || TASK=""

# Get plan status
PLAN=$("$MNEMO" tool mnemo_plan --action status 2>/dev/null) || PLAN=""

# Output rich context block
cat << EOF
<mnemo-context>
## Session Loaded
Time: $(date '+%Y-%m-%d %H:%M:%S %Z')
Working Directory: $(pwd)

$RECALL
EOF

# Add active task if present
if [ -n "$TASK" ] && echo "$TASK" | grep -q "task_id"; then
  cat << EOF

## Active Task
$TASK
EOF
fi

# Add plan status if present
if [ -n "$PLAN" ] && echo "$PLAN" | grep -qv "No active plans"; then
  cat << EOF

## Plan Status
$PLAN
EOF
fi

cat << EOF

## Guidelines
- Search memory before asking the user (mnemo_search_memory)
- Record decisions with mnemo_decide (they persist forever)
- Use mnemo_remember for important context
- Check mnemo_graph for code relationships
- Learnings are auto-captured at session end
</mnemo-context>
EOF

echo "✅ [Mnemo] Full context loaded." >&2
exit 0
""")

    _write_hook(hooks_dir / "user-prompt-submit.sh", f"""#!/bin/sh
# Mnemo userPromptSubmit hook — searches relevant memories for current prompt
# stdout → injected as context before the prompt | stderr → warnings
# Fail-safe: always exits 0

MNEMO="{mnemo_bin}"

# Read STDIN (Kiro sends JSON with .message or .prompt)
input_json=$(cat 2>/dev/null || echo "{{}}")

# Extract user message
USER_PROMPT=""
if command -v jq >/dev/null 2>&1; then
  USER_PROMPT=$(echo "$input_json" | jq -r '.message // .prompt // .content // empty' 2>/dev/null) || true
fi

# Fallback: try simple grep extraction
if [ -z "$USER_PROMPT" ]; then
  USER_PROMPT=$(echo "$input_json" | grep -o '"message":"[^"]*"' | head -1 | sed 's/"message":"//;s/"$//') || true
fi

# Skip if no prompt or too short
if [ -z "$USER_PROMPT" ] || [ ${{#USER_PROMPT}} -lt 10 ]; then
  exit 0
fi

# Skip simple greetings and acknowledgments
LOWER_PROMPT=$(echo "$USER_PROMPT" | tr '[:upper:]' '[:lower:]')
case "$LOWER_PROMPT" in
  "hi"|"hello"|"hey"|"thanks"|"thank you"|"ok"|"okay"|"yes"|"no"|"sure"|"got it"|"cool")
    exit 0 ;;
esac

# Search for relevant memories (truncate query to 100 chars)
QUERY=$(echo "$USER_PROMPT" | head -c 100)
RESULTS=$("$MNEMO" tool mnemo_search_memory --query "$QUERY" 2>/dev/null) || RESULTS=""

# Only output if we found relevant results
if [ -n "$RESULTS" ] && echo "$RESULTS" | grep -qv "No results"; then
  RESULT_COUNT=$(echo "$RESULTS" | grep -c "^-" 2>/dev/null || echo "0")
  if [ "$RESULT_COUNT" -gt 0 ]; then
    cat << EOF
<mnemo-relevant-context>
$RESULTS
</mnemo-relevant-context>
EOF
  fi
fi

exit 0
""")

    _write_hook(hooks_dir / "pre-tool-use.sh", """#!/bin/sh
# Mnemo preToolUse hook — security validation before shell execution
# exit 0 = allow | exit 1 = block
# Only triggers for shell tool (via matcher in agent config)

# Read STDIN (Kiro sends JSON with tool_name and tool_input)
input_json=$(cat 2>/dev/null || echo "{}")

# Extract tool input/command
TOOL_INPUT=""
if command -v jq >/dev/null 2>&1; then
  TOOL_INPUT=$(echo "$input_json" | jq -r '.tool_input.command // .tool_input // empty' 2>/dev/null) || true
fi

# If we can't parse input, allow (fail-open for usability)
if [ -z "$TOOL_INPUT" ]; then
  exit 0
fi

# Block catastrophic commands
if echo "$TOOL_INPUT" | grep -qE 'rm -rf /($| )|rm -rf ~|rm -rf \\$HOME|> /dev/sd|dd if=/dev/zero|mkfs\\.' 2>/dev/null; then
  echo "🚨 [Mnemo Security] BLOCKED: Catastrophic command detected" >&2
  echo "Command: $(echo "$TOOL_INPUT" | head -c 80)" >&2
  exit 1
fi

# Block remote code execution patterns
if echo "$TOOL_INPUT" | grep -qE 'curl.*\\|.*(sh|bash)|wget.*\\|.*(sh|bash)' 2>/dev/null; then
  echo "🚨 [Mnemo Security] BLOCKED: Remote code execution pattern" >&2
  exit 1
fi

# Block system directory modifications
if echo "$TOOL_INPUT" | grep -qE '(>|>>|tee|mv|rm|chmod|chown).*/etc/|.*/usr/bin|.*/sbin' 2>/dev/null; then
  echo "⛔ [Mnemo Security] BLOCKED: System directory modification" >&2
  exit 1
fi

# Block credential exfiltration
if echo "$TOOL_INPUT" | grep -qE 'cat.*(\\. env|credentials|\\.aws/credentials|id_rsa|\\.ssh/)|curl.*(-d|--data).*(password|token|secret)' 2>/dev/null; then
  echo "⚠️ [Mnemo Security] BLOCKED: Potential credential access/exfiltration" >&2
  exit 1
fi

# Allow everything else
exit 0
""")

    _write_hook(hooks_dir / "post-tool-use.sh", """#!/bin/sh
# Mnemo postToolUse — track file modifications
input_json=$(cat 2>/dev/null || echo "{}")
exit 0
""")

    _write_hook(hooks_dir / "stop.sh", f"""#!/bin/sh
# Mnemo stop hook — auto-captures learnings from session responses
# Reads STDIN (the agent's final response), detects learning patterns, saves them
# Fail-safe: always exits 0

MNEMO="{mnemo_bin}"

# Read STDIN (Kiro sends JSON with .response or .content)
input_json=$(cat 2>/dev/null || echo "{{}}")

# Extract response text
RESPONSE=""
if command -v jq >/dev/null 2>&1; then
  RESPONSE=$(echo "$input_json" | jq -r '.response // .content // .message // .text // empty' 2>/dev/null) || true
fi

# If no response, just exit
if [ -z "$RESPONSE" ] || [ ${{#RESPONSE}} -lt 100 ]; then
  exit 0
fi

# Detect learning patterns in the response
LOWER_RESPONSE=$(echo "$RESPONSE" | tr '[:upper:]' '[:lower:]')

# Count learning indicators
LEARNING_SCORE=0
echo "$LOWER_RESPONSE" | grep -q "fixed\\|solved\\|resolved" && LEARNING_SCORE=$((LEARNING_SCORE + 1))
echo "$LOWER_RESPONSE" | grep -q "the issue was\\|the problem was\\|root cause\\|the bug was" && LEARNING_SCORE=$((LEARNING_SCORE + 1))
echo "$LOWER_RESPONSE" | grep -q "discovered\\|realized\\|figured out\\|learned\\|turned out" && LEARNING_SCORE=$((LEARNING_SCORE + 1))
echo "$LOWER_RESPONSE" | grep -q "solution\\|the fix\\|working now\\|now works" && LEARNING_SCORE=$((LEARNING_SCORE + 1))

# If 2+ indicators, this response contains a learning
if [ "$LEARNING_SCORE" -ge 2 ]; then
  SUMMARY=""
  SUMMARY=$(echo "$RESPONSE" | grep -ioE "(the issue was|the problem was|root cause was)[^.]*\\." | head -1 | head -c 150)
  if [ -z "$SUMMARY" ]; then
    SUMMARY=$(echo "$RESPONSE" | grep -ioE "(fixed by|solved by|resolved by|the fix was)[^.]*\\." | head -1 | head -c 150)
  fi
  if [ -z "$SUMMARY" ]; then
    SUMMARY=$(echo "$RESPONSE" | grep -ioE "(discovered|realized|figured out|learned) (that )?[^.]*\\." | head -1 | head -c 150)
  fi
  if [ -z "$SUMMARY" ]; then
    SUMMARY=$(echo "$RESPONSE" | grep -iE "fixed|solved|resolved|discovered|learned" | head -1 | head -c 150)
  fi

  if [ -n "$SUMMARY" ] && [ ${{#SUMMARY}} -gt 20 ]; then
    "$MNEMO" tool mnemo_remember --content "Auto-learned: $SUMMARY" --category "pattern" 2>/dev/null || true
    echo "📚 [Mnemo] Learning auto-captured." >&2
  fi
fi

# Detect decisions in the response
echo "$LOWER_RESPONSE" | grep -q "decided to\\|decision:\\|chose to\\|going with\\|we'll use\\|architecture:" && {{
  DECISION=$(echo "$RESPONSE" | grep -iE "decided to|decision:|chose to|going with" | head -1 | head -c 200)
  if [ -n "$DECISION" ] && [ ${{#DECISION}} -gt 20 ]; then
    "$MNEMO" tool mnemo_remember --content "Session decision: $DECISION" --category "general" 2>/dev/null || true
  fi
}}

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
