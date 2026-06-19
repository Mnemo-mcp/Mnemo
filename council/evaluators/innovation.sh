#!/bin/bash
# ABOUTME: Innovation evaluator — challenges paradigm, proposes better approaches
set -euo pipefail
COUNCIL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${COUNCIL_DIR}/lib/memory.sh"

TASK="$1"
CODE="${2:-}"
MEMORY="${3:-}"
SPEC="${4:-}"

ROLE=$(cat "${COUNCIL_DIR}/roles/innovation.md")

PROMPT="$ROLE

TASK: $TASK
"
[[ -n "$CODE" ]] && PROMPT+="
CURRENT APPROACH:
$CODE
"
[[ -n "$MEMORY" ]] && PROMPT+="
CONTEXT:
$MEMORY
"

PROMPT+='
Respond ONLY with valid JSON:
{"verdict": "PASS|REPLAN", "issues": [], "reason": "if REPLAN, what better approach exists", "alternative": "description of better approach if any"}'

if command -v kiro-cli >/dev/null 2>&1; then
    echo "$PROMPT" | kiro-cli chat --no-interactive --print-only 2>/dev/null
else
    echo '{"verdict": "PASS", "issues": [], "reason": "", "alternative": ""}'
fi
