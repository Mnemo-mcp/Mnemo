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

  "prompt": "You are an engineering assistant powered by Mnemo — a persistent memory system.\\n\\n## Context Loading\\n\\nYour project context is AUTOMATICALLY loaded at session start by the agentSpawn hook. You already have it as <mnemo-context>. You do NOT need to call mnemo_recall yourself — it was already done.\\n\\nIf context appears missing, use the MCP tool `mnemo_recall`. NEVER read .mnemo/ files. All memory operations are MCP tool calls only.\\n\\n## Memory Responsibilities\\n\\nHooks auto-capture user decisions from their messages. YOUR job is to persist context that only YOU can see:\\n\\n### Call `mnemo_decide` when:\\n- You make or confirm an architectural choice (database, framework, pattern, deployment target)\\n- You choose between approaches during implementation\\n- The user approves a technical direction you proposed\\n\\n### Call `mnemo_remember` when:\\n- You discover something about the codebase through investigation (category: architecture)\\n- You fix a bug — save root cause + fix (category: bug)\\n- You identify a pattern or convention in the code (category: pattern)\\n- You learn a user preference through their feedback (category: preference)\\n\\n### Call `mnemo_search_memory` before:\\n- Asking the user a question (they may have answered in a past session)\\n- Making assumptions about the project setup\\n\\n### Do NOT remember:\\n- Temporary debugging output\\n- Things obvious from the code itself\\n- File paths you modified (noise)\\n\\n## Tools\\n\\n- `mnemo_plan` — task tracking (create, status, done)\\n- `mnemo_graph` — code knowledge graph (neighbors, stats, find)\\n- `mnemo_lookup` — 360° symbol/service details\\n- `mnemo_search` — hybrid search (code + memory + APIs)\\n- `mnemo_impact` — blast radius analysis\\n- `mnemo_audit` — security, health, conventions\\n\\n## Memory Slots\\n\\nUse `mnemo_slot_set`/`mnemo_slot_get` for structured context: project_context, user_preferences, conventions, pending_items, known_gotchas.",

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

## What Hooks Handle (automatic, you don't need to do this)

- **Session start**: context loaded automatically via agentSpawn hook
- **User decisions**: user-prompt-submit hook detects naming, preferences, corrections from user messages
- **Bug fix detection**: stop hook detects learning patterns from your responses
- **Security**: pre-tool-use hook blocks dangerous commands

## What YOU Must Handle (hooks can't see this)

Hooks only see user messages and your final response. They can't see what you discover DURING work. You must persist:

| When | Tool | Category |
|------|------|----------|
| You choose an approach | `mnemo_decide` | — |
| You discover how the codebase works | `mnemo_remember` | architecture |
| You fix a bug | `mnemo_remember` | bug |
| You notice a pattern/convention | `mnemo_remember` | pattern |
| User gives feedback on your work | `mnemo_remember` | preference |

## Tool Reference

| Tool | Purpose |
|------|---------|
| `mnemo_recall` | Load context (auto-called at start) |
| `mnemo_remember` | Store context (architecture, bug, pattern, preference, general) |
| `mnemo_decide` | Permanent architectural decision (never evicted) |
| `mnemo_forget` | Delete a memory by ID |
| `mnemo_search_memory` | Search past memories |
| `mnemo_lookup` | 360° symbol/service details |
| `mnemo_search` | Hybrid search: code + memory + APIs |
| `mnemo_graph` | Knowledge graph queries |
| `mnemo_impact` | Blast radius analysis |
| `mnemo_plan` | Task tracking (create, status, done, add) |
| `mnemo_audit` | Security, health, conventions |
| `mnemo_record` | Errors, incidents, reviews, corrections |
| `mnemo_generate` | Commit/PR descriptions |
| `mnemo_map` | Regenerate repo map |
| `mnemo_lesson` | Learned patterns with decay |

## Memory Slots

Structured context via `mnemo_slot_set`/`mnemo_slot_get`:
- `project_context` — what this project is
- `user_preferences` — style, conventions
- `pending_items` — follow-ups
- `known_gotchas` — pitfalls

## Rules

- All operations are MCP tool calls to the 'mnemo' server
- NEVER read .mnemo/ files directly
- Search memory before asking the user a question
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

# Hive: pull latest team knowledge (silent, non-blocking)
HIVE_DIR="$HOME/.mnemo/hive"
if [ -d "$HIVE_DIR/.git" ]; then
  git -C "$HIVE_DIR" pull --ff-only >/dev/null 2>&1 || true
fi

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
- Search Hive for team knowledge: mnemo hive search "topic"
- Learnings are auto-captured at session end
</mnemo-context>
EOF

echo "✅ [Mnemo] Full context loaded." >&2
exit 0
""")

    _write_hook(hooks_dir / "user-prompt-submit.sh", f"""#!/bin/sh
# Mnemo userPromptSubmit hook — AI-powered decision detection + memory search
# Uses embedding-based intent classification (not regex) to auto-persist user decisions
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

# Skip simple greetings
LOWER_PROMPT=$(echo "$USER_PROMPT" | tr '[:upper:]' '[:lower:]')
case "$LOWER_PROMPT" in
  "hi"|"hello"|"hey"|"thanks"|"thank you"|"ok"|"okay"|"yes"|"no"|"sure"|"got it"|"cool"|"looks good"|"lgtm"|"nice"|"great"|"perfect"|"continue")
    exit 0 ;;
esac

# --- AUTO-CAPTURE: AI-based intent classification ---
# Classifies message using embedding similarity (~1ms, no external APIs)
CAPTURE_RESULT=$("$MNEMO" tool auto_capture --message "$USER_PROMPT" 2>/dev/null) || CAPTURE_RESULT=""
if echo "$CAPTURE_RESULT" | grep -q "^captured"; then
  echo "📌 [Mnemo] Auto-captured: $CAPTURE_RESULT" >&2
fi

# --- MEMORY SEARCH ---
QUERY=$(echo "$USER_PROMPT" | head -c 100)
RESULTS=$("$MNEMO" tool mnemo_search_memory --query "$QUERY" 2>/dev/null) || RESULTS=""

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

    _write_hook(hooks_dir / "post-tool-use.sh", f"""#!/bin/sh
# Mnemo postToolUse — captures meaningful tool outcomes
# Captures: failed commands, new file creation patterns, test results
# Fail-safe: always exits 0, must complete within 3s timeout

MNEMO="{mnemo_bin}"
input_json=$(cat 2>/dev/null || echo "{{}}")

# Extract tool info
TOOL_NAME=""
TOOL_SUCCESS="true"
EXIT_STATUS=""
FILE_PATH=""
if command -v jq >/dev/null 2>&1; then
  TOOL_NAME=$(echo "$input_json" | jq -r '.tool_name // .toolName // "unknown"' 2>/dev/null) || TOOL_NAME="unknown"
  TOOL_SUCCESS=$(echo "$input_json" | jq -r '.tool_response.success // "true"' 2>/dev/null) || TOOL_SUCCESS="true"
  EXIT_STATUS=$(echo "$input_json" | jq -r '.tool_response.exit_status // empty' 2>/dev/null) || EXIT_STATUS=""
  FILE_PATH=$(echo "$input_json" | jq -r '.tool_input.path // .tool_input.file_path // empty' 2>/dev/null) || FILE_PATH=""
fi

[ "$TOOL_NAME" = "unknown" ] && exit 0

case "$TOOL_NAME" in
  # Track failed commands — debugging signal
  shell|bash)
    if [ "$TOOL_SUCCESS" = "false" ] || echo "$EXIT_STATUS" | grep -qv "^exit status: 0$"; then
      CMD=$(echo "$input_json" | jq -r '.tool_input.command // empty' 2>/dev/null | head -c 100) || true
      ERROR=$(echo "$input_json" | jq -r '.tool_response.stderr // empty' 2>/dev/null | head -c 150) || true
      if [ -n "$CMD" ] && [ -n "$ERROR" ]; then
        printf '%s' "Command failed: $CMD → $ERROR" | "$MNEMO" tool mnemo_remember --content "$(cat)" --category "bug" 2>/dev/null || true
      fi
    fi
    ;;
  # Track new file creation — records what conventions the agent followed
  write|create)
    if [ -n "$FILE_PATH" ]; then
      # Only track source files, not config/temp
      case "$FILE_PATH" in
        *.java|*.py|*.ts|*.js|*.go|*.rs|*.cs)
          # Extract class/function name from path
          FILENAME=$(basename "$FILE_PATH")
          DIRNAME=$(dirname "$FILE_PATH" | sed 's|.*/src/||' | sed 's|/|.|g')
          "$MNEMO" tool mnemo_remember --content "Created: ${FILENAME} in ${DIRNAME}" --category "general" 2>/dev/null || true
          ;;
      esac
    fi
    ;;
esac

exit 0
""")

    _write_hook(hooks_dir / "stop.sh", f"""#!/bin/sh
# Mnemo stop hook — auto-captures learnings, decisions, and context from session
# Reads STDIN (the agent's final response), detects patterns worth saving
# Fail-safe: always exits 0

MNEMO="{mnemo_bin}"

# Read STDIN
input_json=$(cat 2>/dev/null || echo "{{}}")

# Extract response text
RESPONSE=""
if command -v jq >/dev/null 2>&1; then
  RESPONSE=$(echo "$input_json" | jq -r '.response // .content // .message // .text // empty' 2>/dev/null) || true
fi

if [ -z "$RESPONSE" ] || [ ${{#RESPONSE}} -lt 50 ]; then
  exit 0
fi

LOWER_RESPONSE=$(echo "$RESPONSE" | tr '[:upper:]' '[:lower:]')

# --- 1. Bug fix / learning detection ---
LEARNING_SCORE=0
echo "$LOWER_RESPONSE" | grep -q "fixed\\|solved\\|resolved" && LEARNING_SCORE=$((LEARNING_SCORE + 1))
echo "$LOWER_RESPONSE" | grep -q "the issue was\\|the problem was\\|root cause\\|the bug was\\|caused by" && LEARNING_SCORE=$((LEARNING_SCORE + 1))
echo "$LOWER_RESPONSE" | grep -q "discovered\\|realized\\|figured out\\|learned\\|turned out\\|the reason" && LEARNING_SCORE=$((LEARNING_SCORE + 1))
echo "$LOWER_RESPONSE" | grep -q "solution\\|the fix\\|working now\\|now works\\|resolved by" && LEARNING_SCORE=$((LEARNING_SCORE + 1))

if [ "$LEARNING_SCORE" -ge 2 ]; then
  SUMMARY=$(echo "$RESPONSE" | grep -ioE "(the issue was|the problem was|root cause was|caused by|fixed by|solved by|the fix was|resolved by)[^.]*\\." | head -1 | head -c 200)
  if [ -z "$SUMMARY" ]; then
    SUMMARY=$(echo "$RESPONSE" | grep -iE "fixed|solved|resolved|discovered|the reason" | head -1 | head -c 200)
  fi
  if [ -n "$SUMMARY" ] && [ ${{#SUMMARY}} -gt 20 ]; then
    printf '%s' "Bug fix: $SUMMARY" | "$MNEMO" tool mnemo_remember --content "$(cat)" --category "bug" 2>/dev/null || true
  fi
fi

# --- 2. Decision detection ---
echo "$LOWER_RESPONSE" | grep -qE "decided to |i'll use |going with |chose |using .* for |setting up .* with " && {{
  DECISION=$(echo "$RESPONSE" | grep -iE "decided to|I'll use|going with|chose|using .* for|setting up .* with" | head -1 | head -c 200)
  if [ -n "$DECISION" ] && [ ${{#DECISION}} -gt 20 ]; then
    printf '%s' "$DECISION" | "$MNEMO" tool mnemo_decide --decision "$(cat)" 2>/dev/null || true
  fi
}}

# --- 3. Context establishment ---
echo "$LOWER_RESPONSE" | grep -qE "your (project|service|app|api|codebase) (uses|is|has)|the (stack|architecture|structure) (is|uses)" && {{
  CONTEXT=$(echo "$RESPONSE" | grep -iE "your (project|service|app|api|codebase)|the (stack|architecture|structure)" | head -2 | head -c 300)
  if [ -n "$CONTEXT" ] && [ ${{#CONTEXT}} -gt 30 ]; then
    "$MNEMO" tool mnemo_remember --content "Project context: $CONTEXT" --category "architecture" 2>/dev/null || true
  fi
}}

# --- 4. Pattern detection ---
echo "$LOWER_RESPONSE" | grep -qE "pattern (is|you|here)|convention (is|you|here)|following the .* pattern" && {{
  PATTERN=$(echo "$RESPONSE" | grep -iE "pattern|convention|follows" | head -1 | head -c 200)
  if [ -n "$PATTERN" ] && [ ${{#PATTERN}} -gt 20 ]; then
    "$MNEMO" tool mnemo_remember --content "Codebase pattern: $PATTERN" --category "pattern" 2>/dev/null || true
  fi
}}

# --- 5. Catch-all: substantial sessions get a summary persisted ---
WORD_COUNT=$(echo "$RESPONSE" | wc -w | tr -d ' ')
if [ "$WORD_COUNT" -gt 150 ]; then
  KEY_LINES=$(echo "$RESPONSE" | grep -iE "^[-*•] |created |implemented |found |discovered |the .* (is|are|uses|has) |added |fixed |built |set up " | head -5 | head -c 500)
  if [ -n "$KEY_LINES" ] && [ ${{#KEY_LINES}} -gt 30 ]; then
    "$MNEMO" tool mnemo_remember --content "Session summary: $KEY_LINES" --category "general" 2>/dev/null || true
  fi
fi

exit 0
""")

    # Generate agent config with RELATIVE paths — Kiro runs hooks from project root
    # Using relative paths ensures hooks work even if the repo directory moves
    config_str = _KIRO_AGENT_CONFIG_TEMPLATE
    config_str = config_str.replace("HOOK_SPAWN_PATH", ".kiro/hooks/agent-spawn.sh")
    config_str = config_str.replace("HOOK_PROMPT_PATH", ".kiro/hooks/user-prompt-submit.sh")
    config_str = config_str.replace("HOOK_PRETOOL_PATH", ".kiro/hooks/pre-tool-use.sh")
    config_str = config_str.replace("HOOK_POSTTOOL_PATH", ".kiro/hooks/post-tool-use.sh")
    config_str = config_str.replace("HOOK_STOP_PATH", ".kiro/hooks/stop.sh")
    config_str = config_str.replace("MCP_BINARY_PATH", mnemo_mcp)

    # Council path — find council/ relative to mnemo package install
    council_dir = Path(__file__).resolve().parent.parent.parent / "council"
    if not council_dir.exists():
        # Fallback: check repo root
        council_dir = repo_root / "council"
    config_str = config_str.replace("COUNCIL_PATH", str(council_dir))

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
    """Install Claude Code hooks via .claude/settings.json + CLAUDE.md + MCP config."""
    import shutil

    mnemo_bin = shutil.which("mnemo") or "mnemo"
    mnemo_mcp = shutil.which("mnemo-mcp") or "mnemo-mcp"

    claude_dir = repo_root / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write .claude/settings.json with hooks
    settings_path = claude_dir / "settings.json"
    existing = {}
    if settings_path.exists():
        try:
            existing = json.loads(settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    existing["hooks"] = {
        "SessionStart": [{
            "hooks": [{
                "type": "command",
                "command": f"{mnemo_bin} tool mnemo_recall"
            }]
        }],
        "UserPromptSubmit": [{
            "hooks": [{
                "type": "command",
                "command": f"{mnemo_bin} tool mnemo_search_memory --query \"$ARGUMENTS\"",
                "timeout": 10
            }]
        }],
        "PreToolUse": [{
            "matcher": "Bash",
            "hooks": [{
                "type": "command",
                "command": f"{mnemo_bin} check",
                "timeout": 5
            }]
        }],
        "PostToolUse": [{
            "matcher": "Write|Edit",
            "hooks": [{
                "type": "command",
                "command": f"{mnemo_bin} tool mnemo_remember --content \"Modified file: ${{tool_input.file_path}}\" --category general",
                "timeout": 5
            }]
        }],
        "Stop": [{
            "hooks": [{
                "type": "command",
                "command": f"{mnemo_bin} tool mnemo_remember --content \"Session ended\" --category general",
                "timeout": 10
            }]
        }],
        "PreCompact": [{
            "hooks": [{
                "type": "command",
                "command": f"{mnemo_bin} tool mnemo_recall"
            }]
        }],
    }

    # Ensure MCP server is configured
    if "mcpServers" not in existing:
        existing["mcpServers"] = {}
    existing["mcpServers"]["mnemo"] = {
        "command": mnemo_mcp,
        "args": [],
    }

    settings_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    # 2. Write/append CLAUDE.md with Mnemo instructions
    claude_md = repo_root / "CLAUDE.md"
    mnemo_section = """
## Mnemo — Persistent Memory

This project uses Mnemo for persistent engineering memory across sessions.

### Available via MCP tools (call directly):
- `mnemo_recall` — load full project context
- `mnemo_remember` — store important decisions, patterns, fixes
- `mnemo_decide` — record permanent architectural decisions
- `mnemo_search_memory` — search past memories semantically
- `mnemo_lookup` — get detailed class/method info
- `mnemo_graph` — explore code relationships
- `mnemo_impact` — analyze upstream/downstream dependencies
- `mnemo_plan` — create and track task plans

### Rules:
- Search memory before asking the user something they may have told you before
- Record decisions with mnemo_decide (they persist forever)
- Use mnemo_remember for important context worth keeping
- Learnings are auto-captured at session end via hooks
"""
    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        if "Mnemo" not in content:
            claude_md.write_text(content + mnemo_section, encoding="utf-8")
    else:
        claude_md.write_text(mnemo_section.lstrip(), encoding="utf-8")

    return (
        f"Claude Code configured:\n"
        f"- Hooks: .claude/settings.json (SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop, PreCompact)\n"
        f"- MCP: mnemo server registered\n"
        f"- Instructions: CLAUDE.md updated\n"
        f"MCP server: {mnemo_mcp}"
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
