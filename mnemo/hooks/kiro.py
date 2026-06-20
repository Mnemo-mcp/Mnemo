"""Kiro lifecycle hooks installation."""

from __future__ import annotations

import stat
from pathlib import Path

from .discovery import find_mnemo_cli, find_mnemo_mcp
from .templates import _KIRO_AGENT_CONFIG_TEMPLATE, _MNEMO_SKILL


def _write_hook(path: Path, content: str) -> None:
    """Write a hook script and make it executable."""
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def install_kiro_hooks(repo_root: Path) -> str:
    """Generate .kiro/agents/mnemo-enhanced.json, hooks, and skill file."""
    mnemo_mcp = find_mnemo_mcp(repo_root)
    mnemo_bin = find_mnemo_cli()

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
          "$MNEMO" tool mnemo_remember --content "Created: ${{FILENAME}} in ${{DIRNAME}}" --category "general" 2>/dev/null || true
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
