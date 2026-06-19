#!/bin/bash
# ABOUTME: Synthesizes evaluator results into a readable council report
set -euo pipefail
COUNCIL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${COUNCIL_DIR}/lib/common.sh"

PHASE="$1"
RESULTS_DIR="$2"

echo "## Council Report ($PHASE)"
echo ""

# Summary table
echo "| Evaluator | Verdict | Key Finding |"
echo "|-----------|---------|-------------|"

for f in "$RESULTS_DIR"/*.json; do
    [[ -f "$f" ]] || continue
    name=$(basename "$f" .json)
    verdict=$(jq -r '.verdict // "PASS"' "$f" 2>/dev/null || echo "PASS")
    issue=$(jq -r '.issues[0] // "None"' "$f" 2>/dev/null || echo "None")
    
    case "$verdict" in
        PASS) icon="✅" ;;
        FAIL) icon="❌" ;;
        REPLAN) icon="🔄" ;;
        *) icon="❓" ;;
    esac
    
    echo "| $name | $icon $verdict | $issue |"
done

echo ""

# Overall verdict
OVERALL=$(collect_verdicts "$RESULTS_DIR")
case "$OVERALL" in
    PASS) echo "### ✅ Overall: PASS — All evaluators satisfied" ;;
    FAIL) 
        echo "### ❌ Overall: NEEDS WORK"
        echo ""
        echo "**Issues to address:**"
        for f in "$RESULTS_DIR"/*.json; do
            [[ -f "$f" ]] || continue
            verdict=$(jq -r '.verdict // "PASS"' "$f" 2>/dev/null || echo "PASS")
            if [[ "$verdict" == "FAIL" ]]; then
                name=$(basename "$f" .json)
                jq -r '.issues[]? // empty' "$f" 2>/dev/null | while read -r issue; do
                    echo "- [$name] $issue"
                done
            fi
        done
        ;;
    REPLAN)
        echo "### 🔄 Overall: REPLAN NEEDED"
        echo ""
        reason=$(get_replan_reason "$RESULTS_DIR")
        echo "**Reason:** $reason"
        ;;
esac
