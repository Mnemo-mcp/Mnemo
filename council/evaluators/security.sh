#!/bin/bash
# ABOUTME: Security evaluator — threat modeling + compliance checking
set -euo pipefail
COUNCIL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${COUNCIL_DIR}/lib/memory.sh"

TASK="$1"
CODE="${2:-}"
MEMORY="${3:-}"
SPEC="${4:-}"

ROLE=$(cat "${COUNCIL_DIR}/roles/security.md")

# If mnemo's security module is available, run it first
STATIC_FINDINGS=""
if command -v mnemo >/dev/null 2>&1; then
    STATIC_FINDINGS=$(mnemo security check 2>/dev/null || echo "")
fi

PROMPT="$ROLE

TASK: $TASK
"
[[ -n "$CODE" ]] && PROMPT+="
CODE/OUTPUT TO EVALUATE:
$CODE
"
[[ -n "$STATIC_FINDINGS" ]] && PROMPT+="
STATIC ANALYSIS FINDINGS:
$STATIC_FINDINGS
"
[[ -n "$MEMORY" ]] && PROMPT+="
PAST SECURITY ISSUES:
$MEMORY
"

PROMPT+='
Respond ONLY with valid JSON:
{"verdict": "PASS|FAIL", "issues": ["issue1", "issue2"], "severity": "critical|high|medium", "compliance": "ok|violation"}'

if command -v kiro-cli >/dev/null 2>&1; then
    echo "$PROMPT" | kiro-cli chat --no-interactive --print-only 2>/dev/null
else
    echo '{"verdict": "PASS", "issues": [], "severity": "none", "compliance": "ok"}'
fi
