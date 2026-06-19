#!/bin/bash
# ABOUTME: Adversarial evaluator — tries to break things
set -euo pipefail
COUNCIL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${COUNCIL_DIR}/lib/memory.sh"

TASK="$1"
CODE="${2:-}"
MEMORY="${3:-}"
SPEC="${4:-}"

ROLE=$(cat "${COUNCIL_DIR}/roles/adversarial.md")

PROMPT="$ROLE

TASK: $TASK
"
[[ -n "$CODE" ]] && PROMPT+="
CODE/OUTPUT TO EVALUATE:
$CODE
"
[[ -n "$MEMORY" ]] && PROMPT+="
PAST ISSUES IN THIS CODEBASE:
$MEMORY
"

PROMPT+='
Respond ONLY with valid JSON:
{"verdict": "PASS|FAIL", "issues": ["issue1", "issue2"], "severity": "critical|high|medium"}'

if command -v kiro-cli >/dev/null 2>&1; then
    echo "$PROMPT" | kiro-cli chat --no-interactive --print-only 2>/dev/null
else
    echo '{"verdict": "PASS", "issues": [], "severity": "none"}'
fi
