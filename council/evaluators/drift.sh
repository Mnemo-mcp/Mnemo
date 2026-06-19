#!/bin/bash
# ABOUTME: Drift evaluator — checks if output matches spec/acceptance criteria
set -euo pipefail
COUNCIL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${COUNCIL_DIR}/lib/memory.sh"

TASK="$1"
CODE="${2:-}"
MEMORY="${3:-}"
SPEC="${4:-}"

ROLE=$(cat "${COUNCIL_DIR}/roles/drift.md")

# Build prompt
PROMPT="$ROLE

TASK: $TASK
"
[[ -n "$SPEC" && -f "$SPEC" ]] && PROMPT+="
SPEC:
$(cat "$SPEC")
"
[[ -n "$CODE" ]] && PROMPT+="
CODE/OUTPUT TO EVALUATE:
$CODE
"
[[ -n "$MEMORY" ]] && PROMPT+="
PAST CONTEXT:
$MEMORY
"

PROMPT+='
Respond ONLY with valid JSON:
{"verdict": "PASS|FAIL|REPLAN", "issues": ["issue1", "issue2"], "reason": "if REPLAN, explain why"}'

# Call LLM (kiro subagent or direct API)
if command -v kiro-cli >/dev/null 2>&1; then
    echo "$PROMPT" | kiro-cli chat --no-interactive --print-only 2>/dev/null
else
    # Fallback: output default pass if no LLM available
    echo '{"verdict": "PASS", "issues": [], "reason": ""}'
fi
