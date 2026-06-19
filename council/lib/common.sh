#!/bin/bash
# ABOUTME: Shared utilities for council scripts
set -euo pipefail

COUNCIL_DIR="${COUNCIL_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
COUNCIL_CACHE="${COUNCIL_CACHE:-/tmp/mnemo-council}"
mkdir -p "$COUNCIL_CACHE"

log() {
    echo "[council] $*" >&2
}

# Collect verdicts from evaluator JSON results
collect_verdicts() {
    local results_dir="$1"
    local has_replan=false has_fail=false
    
    for f in "$results_dir"/*.json; do
        [[ -f "$f" ]] || continue
        local verdict
        verdict=$(jq -r '.verdict // "PASS"' "$f" 2>/dev/null || echo "PASS")
        case "$verdict" in
            REPLAN) has_replan=true ;;
            FAIL) has_fail=true ;;
        esac
    done
    
    if [[ "$has_replan" == true ]]; then echo "REPLAN"
    elif [[ "$has_fail" == true ]]; then echo "FAIL"
    else echo "PASS"
    fi
}

# Collect failure feedback for generator
collect_feedback() {
    local results_dir="$1"
    local feedback=""
    
    for f in "$results_dir"/*.json; do
        [[ -f "$f" ]] || continue
        local name verdict issues
        name=$(basename "$f" .json)
        verdict=$(jq -r '.verdict // "PASS"' "$f" 2>/dev/null || echo "PASS")
        if [[ "$verdict" == "FAIL" ]]; then
            issues=$(jq -r '.issues[]? // empty' "$f" 2>/dev/null || echo "")
            feedback+="[$name] $issues"$'\n'
        fi
    done
    echo "$feedback"
}

# Get replan reason from results
get_replan_reason() {
    local results_dir="$1"
    for f in "$results_dir"/*.json; do
        [[ -f "$f" ]] || continue
        local verdict reason
        verdict=$(jq -r '.verdict // "PASS"' "$f" 2>/dev/null || echo "PASS")
        if [[ "$verdict" == "REPLAN" ]]; then
            reason=$(jq -r '.reason // "No reason given"' "$f" 2>/dev/null)
            echo "$reason"
            return
        fi
    done
    echo "Unknown"
}
