#!/bin/bash
# ABOUTME: Generator — produces code/tests/fix based on task + feedback
set -euo pipefail
COUNCIL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TASK="$1"
CODE_CONTEXT="${2:-}"
MEMORY_CONTEXT="${3:-}"
SPEC="${4:-}"
FEEDBACK="${5:-}"

PROMPT="You are a code generator. Produce the implementation for this task.

TASK: $TASK
"
[[ -n "$SPEC" && -f "$SPEC" ]] && PROMPT+="
SPEC:
$(cat "$SPEC")
"
[[ -n "$CODE_CONTEXT" ]] && PROMPT+="
EXISTING CODE CONTEXT:
$CODE_CONTEXT
"
[[ -n "$MEMORY_CONTEXT" ]] && PROMPT+="
RELEVANT PAST CONTEXT:
$MEMORY_CONTEXT
"
[[ -n "$FEEDBACK" ]] && PROMPT+="
PREVIOUS ITERATION FEEDBACK (fix these issues):
$FEEDBACK
"

PROMPT+="

Rules:
- Match existing code patterns and conventions
- Complete implementation (no TODOs)
- Handle errors on every external call
- If you discover the plan is impossible, start your response with CONSTRAINT_DISCOVERED:

Output the code/implementation directly."

if command -v kiro-cli >/dev/null 2>&1; then
    echo "$PROMPT" | kiro-cli chat --no-interactive --print-only 2>/dev/null
else
    echo "ERROR: No LLM available for generation" >&2
    exit 1
fi
