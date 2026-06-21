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
# Mnemo agentSpawn hook — injects full context: recall + learnings + graph shape
echo "[$(date +%H:%M:%S)] agent-spawn FIRED" >> .mnemo/hooks.log
# stdout → injected into agent context | stderr → warnings
# Fail-safe: always exits 0

MNEMO="{mnemo_bin}"
input_json=$(cat 2>/dev/null || echo "{{}}")

# --- Core recall (decisions, hot memories, plan, repo map) ---
RECALL=$("$MNEMO" tool mnemo_recall 2>/dev/null) || RECALL=""

if [ -z "$RECALL" ]; then
  echo "<mnemo-context>"
  echo "Mnemo not initialized. Run: mnemo init --client kiro"
  echo "</mnemo-context>"
  exit 0
fi

# --- Learnings (top by confidence — patterns, pitfalls, architecture) ---
LEARNINGS=$("$MNEMO" learnings --limit 7 2>/dev/null) || LEARNINGS=""

# --- Graph stats (project shape) ---
STATS=$("$MNEMO" tool mnemo_graph --action stats 2>/dev/null) || STATS=""

# --- Active plan/task ---
PLAN=$("$MNEMO" tool mnemo_plan --action status 2>/dev/null) || PLAN=""

# Output context block
cat << EOF
<mnemo-context>
## Project Context
$RECALL
EOF

if [ -n "$LEARNINGS" ]; then
  cat << EOF

## Learnings (what we know about this codebase)
$LEARNINGS
EOF
fi

if [ -n "$STATS" ]; then
  cat << EOF

## Codebase Shape
$STATS
EOF
fi

if [ -n "$PLAN" ] && echo "$PLAN" | grep -qv "No active"; then
  cat << EOF

## Active Plan
$PLAN
EOF
fi

echo "</mnemo-context>"
echo "\u2705 [Mnemo] Context loaded." >&2
exit 0
""")

    _write_hook(hooks_dir / "user-prompt-submit.sh", rf"""#!/bin/sh
# Mnemo userPromptSubmit hook — FULL RAG: memory + code graph + symbol lookup
echo "[$(date +%H:%M:%S)] user-prompt-submit FIRED" >> .mnemo/hooks.log
# stdout → injected as context | stderr → warnings | Fail-safe: always exits 0

MNEMO="{mnemo_bin}"

# If agentSpawn did not fire (e.g., agent switch mid-session), load context on first prompt
if [ ! -f "/tmp/.mnemo-session-loaded" ]; then
  touch "/tmp/.mnemo-session-loaded"
  RECALL=$("$MNEMO" tool mnemo_recall --tier compact 2>/dev/null) || RECALL=""
  LEARNINGS=$("$MNEMO" learnings --limit 5 2>/dev/null) || LEARNINGS=""
  if [ -n "$RECALL" ]; then
    echo "<mnemo-context>"
    echo "$RECALL"
    if [ -n "$LEARNINGS" ]; then
      echo ""
      echo "## Learnings"
      echo "$LEARNINGS"
    fi
    echo "</mnemo-context>"
  fi
fi

# Read STDIN
input_json=$(cat 2>/dev/null || echo "{{}}")

# Extract user message
USER_PROMPT=""
if command -v jq >/dev/null 2>&1; then
  USER_PROMPT=$(echo "$input_json" | jq -r '.message // .prompt // .content // empty' 2>/dev/null) || true
fi
if [ -z "$USER_PROMPT" ]; then
  USER_PROMPT=$(echo "$input_json" | grep -o '"message":"[^"]*"' | head -1 | sed 's/"message":"//;s/"$//') || true
fi

if [ -z "$USER_PROMPT" ] || [ ${{#USER_PROMPT}} -lt 10 ]; then
  exit 0
fi
LOWER_PROMPT=$(echo "$USER_PROMPT" | tr '[:upper:]' '[:lower:]')
case "$LOWER_PROMPT" in
  "hi"|"hello"|"hey"|"thanks"|"thank you"|"ok"|"okay"|"yes"|"no"|"sure"|"got it"|"cool"|"looks good"|"lgtm"|"nice"|"great"|"perfect"|"continue")
    exit 0 ;;
esac

# --- AUTO-CAPTURE (only declarative statements) ---
case "$LOWER_PROMPT" in
  what\ *|how\ *|why\ *|where\ *|when\ *|who\ *|which\ *|is\ *|are\ *|can\ *|could\ *|does\ *|do\ *|will\ *)
    ;;
  run\ *|check\ *|show\ *|tell\ *|find\ *|look\ *|list\ *|create\ *|add\ *|fix\ *|implement\ *|refactor\ *|debug\ *|generate\ *|also\ *|include\ *)
    ;;
  *)
    "$MNEMO" tool mnemo_auto_capture --message "$USER_PROMPT" 2>/dev/null || true
    ;;
esac

# --- FULL RAG INJECTION: memory + code graph + symbol lookup ---
QUERY=$(echo "$USER_PROMPT" | head -c 100)
HAS_RESULTS=0
OUTPUT=""

# 1. Memory search
MEMORY=$("$MNEMO" tool mnemo_search_memory --query "$QUERY" 2>/dev/null) || MEMORY=""
if [ -n "$MEMORY" ] && echo "$MEMORY" | grep -qv "No results"; then
  OUTPUT="## Relevant Memories
$MEMORY"
  HAS_RESULTS=1
fi

# 2. Code search (local + all linked repos)
CODE=$("$MNEMO" tool mnemo_cross_search --query "$QUERY" 2>/dev/null) || CODE=""
if [ -n "$CODE" ] && echo "$CODE" | grep -q "^-\|#"; then
  OUTPUT="$OUTPUT

## Relevant Code (all repos)
$CODE"
  HAS_RESULTS=1
fi

# 3. Symbol lookup if PascalCase word found
SYMBOL=$(echo "$USER_PROMPT" | grep -oE '[A-Z][a-zA-Z0-9]{{3,}}' | head -1)
if [ -n "$SYMBOL" ]; then
  LOOKUP=$("$MNEMO" tool mnemo_lookup --symbol "$SYMBOL" 2>/dev/null) || LOOKUP=""
  if [ -n "$LOOKUP" ] && echo "$LOOKUP" | grep -qv "not found" && [ ${{#LOOKUP}} -gt 20 ]; then
    OUTPUT="$OUTPUT

## $SYMBOL
$LOOKUP"
    HAS_RESULTS=1
  fi
fi

if [ "$HAS_RESULTS" -eq 1 ]; then
  cat << EOF
<mnemo-relevant-context>
$OUTPUT
</mnemo-relevant-context>
EOF
fi

exit 0
""")

    _write_hook(hooks_dir / "pre-tool-use.sh", f"""#!/bin/sh
# Mnemo preToolUse — security + impact analysis before tool execution
# exit 0 = allow | exit 2 = block (stderr returned to LLM)
# Fail-safe: defaults to allow

MNEMO="{mnemo_bin}"
input_json=$(cat 2>/dev/null || echo "{{}}")

TOOL_NAME=""
FILE_PATH=""
COMMAND=""
if command -v jq >/dev/null 2>&1; then
  TOOL_NAME=$(echo "$input_json" | jq -r '.tool_name // "unknown"' 2>/dev/null) || TOOL_NAME="unknown"
  FILE_PATH=$(echo "$input_json" | jq -r '.tool_input.path // .tool_input.file_path // empty' 2>/dev/null) || FILE_PATH=""
  COMMAND=$(echo "$input_json" | jq -r '.tool_input.command // empty' 2>/dev/null) || COMMAND=""
fi

case "$TOOL_NAME" in
  # --- SHELL SECURITY ---
  shell|bash|execute_bash)
    [ -z "$COMMAND" ] && exit 0
    # Block catastrophic
    if echo "$COMMAND" | grep -qE 'rm -rf /($| )|rm -rf ~|rm -rf \\$HOME|> /dev/sd|dd if=/dev/zero|mkfs\\.' 2>/dev/null; then
      echo "BLOCKED: Catastrophic command: $(echo "$COMMAND" | head -c 80)" >&2
      exit 2
    fi
    # Block RCE
    if echo "$COMMAND" | grep -qE 'curl.*\\|.*(sh|bash)|wget.*\\|.*(sh|bash)' 2>/dev/null; then
      echo "BLOCKED: Remote code execution pattern" >&2
      exit 2
    fi
    # Block system dir mods
    if echo "$COMMAND" | grep -qE '(>|>>|tee|mv|rm|chmod|chown).*/etc/|.*/usr/bin|.*/sbin' 2>/dev/null; then
      echo "BLOCKED: System directory modification" >&2
      exit 2
    fi
    # Block credential exfil
    if echo "$COMMAND" | grep -qE 'cat.*(\\. env|credentials|\\.aws/|id_rsa|\\.ssh/)|curl.*(-d|--data).*(password|token|secret)' 2>/dev/null; then
      echo "BLOCKED: Credential access/exfiltration" >&2
      exit 2
    fi
    ;;

  # --- FILE WRITE: Show impact before editing (local + cross-repo) ---
  write|fs_write|edit)
    if [ -n "$FILE_PATH" ]; then
      IMPACT=$("$MNEMO" tool mnemo_cross_impact --query "$FILE_PATH" 2>/dev/null) || IMPACT=""
      if [ -n "$IMPACT" ] && echo "$IMPACT" | grep -q "depend"; then
        echo "\n[Mnemo] ⚠️ Impact warning for $FILE_PATH:"
        echo "$IMPACT" | head -5
      fi
    fi
    ;;
esac

exit 0
""")

    _write_hook(hooks_dir / "post-tool-use.sh", f"""#!/bin/sh
# Mnemo postToolUse — security scan + error capture + file tracking
# stdout → added to context | Fail-safe: always exits 0

MNEMO="{mnemo_bin}"
input_json=$(cat 2>/dev/null || echo "{{}}")

TOOL_NAME=""
TOOL_SUCCESS="true"
EXIT_STATUS=""
FILE_PATH=""
COMMAND=""
if command -v jq >/dev/null 2>&1; then
  TOOL_NAME=$(echo "$input_json" | jq -r '.tool_name // "unknown"' 2>/dev/null) || TOOL_NAME="unknown"
  TOOL_SUCCESS=$(echo "$input_json" | jq -r '.tool_response.success // "true"' 2>/dev/null) || TOOL_SUCCESS="true"
  EXIT_STATUS=$(echo "$input_json" | jq -r '.tool_response.exit_status // empty' 2>/dev/null) || EXIT_STATUS=""
  FILE_PATH=$(echo "$input_json" | jq -r '.tool_input.path // .tool_input.file_path // empty' 2>/dev/null) || FILE_PATH=""
  COMMAND=$(echo "$input_json" | jq -r '.tool_input.command // empty' 2>/dev/null) || COMMAND=""
fi

[ "$TOOL_NAME" = "unknown" ] && exit 0

case "$TOOL_NAME" in
  # --- FAILED SHELL: Store error for future reference ---
  shell|bash|execute_bash)
    if [ "$TOOL_SUCCESS" = "false" ] || ([ -n "$EXIT_STATUS" ] && echo "$EXIT_STATUS" | grep -qv "exit status: 0"); then
      ERROR=$(echo "$input_json" | jq -r '.tool_response.stderr // empty' 2>/dev/null | head -c 200) || ERROR=""
      if [ -n "$COMMAND" ] && [ -n "$ERROR" ]; then
        "$MNEMO" learn --type investigation --key "cmd-fail-$(echo "$COMMAND" | md5 -q 2>/dev/null | head -c 8 || echo $$)" \
          --insight "Command failed: $(echo "$COMMAND" | head -c 80) → Error: $(echo "$ERROR" | head -c 120)" \
          --confidence 6 2>/dev/null || true
      fi
    fi
    ;;

  # --- FILE WRITE: Security scan + convention check ---
  write|fs_write|edit)
    if [ -n "$FILE_PATH" ]; then
      case "$FILE_PATH" in
        *.java|*.py|*.ts|*.js|*.go|*.rs|*.cs|*.rb|*.php)
          # Quick security scan on the written file
          SEC=$("$MNEMO" tool mnemo_check_security --file "$FILE_PATH" 2>/dev/null) || SEC=""
          if [ -n "$SEC" ] && echo "$SEC" | grep -qiE "HIGH|CRITICAL"; then
            echo "[Mnemo] 🚨 Security issue in $FILE_PATH:"
            echo "$SEC" | grep -iE "HIGH|CRITICAL" | head -3
          fi
          ;;
      esac
    fi
    ;;
esac

exit 0
""")

    _write_hook(hooks_dir / "stop.sh", f"""#!/bin/sh
# Mnemo stop hook
echo "[$(date +%H:%M:%S)] stop FIRED" >> .mnemo/hooks.log — extracts knowledge from full session transcript
# Safety net: captures what the agent forgot to persist
# Fail-safe: always exits 0

MNEMO="{mnemo_bin}"

# Read STDIN (Kiro's stop event)
input_json=$(cat 2>/dev/null || echo "{{}}")

# --- ETL: Run mnemo ingest on latest session (idempotent, watermarked) ---
"$MNEMO" ingest 2>/dev/null || true

# --- Strategy 1: Read full session transcript (fallback pattern matching) ---
SESSION_DIR="$HOME/.kiro/sessions/cli"
if [ -d "$SESSION_DIR" ]; then
  # Find most recent .jsonl file (current session)
  LATEST=$(ls -t "$SESSION_DIR"/*.jsonl 2>/dev/null | head -1)
  if [ -n "$LATEST" ] && [ -f "$LATEST" ]; then
    # Extract assistant messages (agent's responses)
    TRANSCRIPT=$(cat "$LATEST" | grep -o '"content":"[^"]*"' 2>/dev/null | sed 's/"content":"//;s/"$//' | tail -50)

    if [ -n "$TRANSCRIPT" ]; then
      LOWER_TRANSCRIPT=$(echo "$TRANSCRIPT" | tr '[:upper:]' '[:lower:]')

      # Bug fix detection across full session
      if echo "$LOWER_TRANSCRIPT" | grep -qE "(the issue was|the problem was|root cause|caused by|the bug was).*(fixed|solved|resolved|the fix)"; then
        BUG_LINE=$(echo "$TRANSCRIPT" | grep -iE "(the issue was|the problem was|root cause|caused by)" | head -1 | head -c 300)
        if [ -n "$BUG_LINE" ] && [ ${{#BUG_LINE}} -gt 30 ]; then
          "$MNEMO" learn --type investigation --key "bug-$(date +%s)" --insight "Bug fix: $BUG_LINE" --confidence 8 2>/dev/null || true
        fi
      fi

      # Architecture discovery across full session
      if echo "$LOWER_TRANSCRIPT" | grep -qE "(uses|follows|structured as|architecture|pipeline|pattern is|convention is)"; then
        ARCH_LINE=$(echo "$TRANSCRIPT" | grep -iE "(architecture|structured as|pipeline|pattern is|uses .* pattern|convention)" | grep -viE "^(what|how|check|run|show)" | head -1 | head -c 300)
        if [ -n "$ARCH_LINE" ] && [ ${{#ARCH_LINE}} -gt 40 ]; then
          "$MNEMO" learn --type architecture --key "arch-$(date +%s)" --insight "$ARCH_LINE" --confidence 7 2>/dev/null || true
        fi
      fi

      # Decision detection across full session
      if echo "$LOWER_TRANSCRIPT" | grep -qE "(decided to|going with|chose|i'll use|using .* because|selected)"; then
        DEC_LINE=$(echo "$TRANSCRIPT" | grep -iE "(decided to|going with|chose|using .* because|selected)" | head -1 | head -c 200)
        if [ -n "$DEC_LINE" ] && [ ${{#DEC_LINE}} -gt 25 ]; then
          "$MNEMO" tool mnemo_decide --decision "$DEC_LINE" 2>/dev/null || true
        fi
      fi
    fi
  fi
fi

# --- Strategy 2: Pattern match on STDIN response (original fallback) ---
RESPONSE=""
if command -v jq >/dev/null 2>&1; then
  RESPONSE=$(echo "$input_json" | jq -r '.response // .content // .message // .text // empty' 2>/dev/null) || true
fi

if [ -n "$RESPONSE" ] && [ ${{#RESPONSE}} -gt 50 ]; then
  LOWER_RESPONSE=$(echo "$RESPONSE" | tr '[:upper:]' '[:lower:]')

  # Bug fix in final response
  LEARNING_SCORE=0
  echo "$LOWER_RESPONSE" | grep -q "fixed\\|solved\\|resolved" && LEARNING_SCORE=$((LEARNING_SCORE + 1))
  echo "$LOWER_RESPONSE" | grep -q "the issue was\\|the problem was\\|root cause\\|caused by" && LEARNING_SCORE=$((LEARNING_SCORE + 1))
  echo "$LOWER_RESPONSE" | grep -q "discovered\\|realized\\|figured out\\|the reason" && LEARNING_SCORE=$((LEARNING_SCORE + 1))

  if [ "$LEARNING_SCORE" -ge 2 ]; then
    SUMMARY=$(echo "$RESPONSE" | grep -ioE "(the issue was|the problem was|root cause|caused by|fixed by|the fix was)[^.]*\\." | head -1 | head -c 200)
    if [ -n "$SUMMARY" ] && [ ${{#SUMMARY}} -gt 20 ]; then
      "$MNEMO" learn --type investigation --key "fix-$(date +%s)" --insight "Bug fix: $SUMMARY" --confidence 8 2>/dev/null || true
    fi
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

    # Workflow skills (investigate, plan, implement, verify, review, ship)
    from ..skills import WORKFLOW_SKILLS
    installed_skills = []
    for skill_name, skill_content in WORKFLOW_SKILLS.items():
        s_dir = repo_root / ".kiro" / "skills" / skill_name
        s_dir.mkdir(parents=True, exist_ok=True)
        s_path = s_dir / "SKILL.md"
        s_path.write_text(skill_content.lstrip(), encoding="utf-8")
        installed_skills.append(skill_name)

    return (
        f"Installed Kiro agent: {path.relative_to(repo_root)}\n"
        f"Installed Kiro hooks: {hooks_dir.relative_to(repo_root)}/\n"
        f"Installed Kiro skill: {skill_path.relative_to(repo_root)}\n"
        f"Installed workflow skills: {', '.join(installed_skills)}\n"
        f"MCP server: {mnemo_mcp}\n"
        f"Switch to it with: /agent mnemo-enhanced"
    )
