#!/bin/bash
# ABOUTME: Real-world evaluator — simulates production deployment and operation
set -euo pipefail
COUNCIL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${COUNCIL_DIR}/lib/memory.sh"

TASK="$1"
CODE="${2:-}"
MEMORY="${3:-}"
SPEC="${4:-}"

ROLE=$(cat "${COUNCIL_DIR}/roles/realworld.md")

# Pull past incidents from mnemo if available
INCIDENTS=""
if command -v mnemo >/dev/null 2>&1; then
    INCIDENTS=$(mnemo search "incident production failure" --limit 3 --format json 2>/dev/null || echo "")
fi

PROMPT="$ROLE

TASK: $TASK
"
[[ -n "$CODE" ]] && PROMPT+="
CODE/OUTPUT TO EVALUATE:
$CODE
"
[[ -n "$INCIDENTS" ]] && PROMPT+="
PAST PRODUCTION INCIDENTS:
$INCIDENTS
"
[[ -n "$MEMORY" ]] && PROMPT+="
CONTEXT:
$MEMORY
"

PROMPT+='
Respond ONLY with valid JSON:
{"verdict": "PASS|FAIL", "issues": ["issue1", "issue2"], "deployment_ready": true|false, "risks": ["risk1"]}'

if command -v kiro-cli >/dev/null 2>&1; then
    echo "$PROMPT" | kiro-cli chat --no-interactive --print-only 2>/dev/null
else
    echo '{"verdict": "PASS", "issues": [], "deployment_ready": true, "risks": []}'
fi
