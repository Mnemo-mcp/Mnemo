#!/bin/bash
# ABOUTME: Optional mnemo memory integration — graceful when mnemo not installed
set -euo pipefail

# Check if mnemo CLI is available
has_mnemo() {
    command -v mnemo >/dev/null 2>&1
}

# Query mnemo for relevant context
memory_query() {
    local task="$1"
    if has_mnemo; then
        mnemo search "$task" --limit 3 --format json 2>/dev/null || echo ""
    else
        echo ""
    fi
}

# Store council findings back to mnemo memory
memory_store() {
    local tag="$1"
    local results_dir="$2"
    
    if ! has_mnemo; then return 0; fi
    
    # Build summary of what evaluators found
    local summary=""
    for f in "$results_dir"/*.json; do
        [[ -f "$f" ]] || continue
        local name verdict issues
        name=$(basename "$f" .json)
        verdict=$(jq -r '.verdict // "PASS"' "$f" 2>/dev/null || echo "PASS")
        issues=$(jq -r '.issues[]? // empty' "$f" 2>/dev/null | head -3 || echo "")
        if [[ -n "$issues" ]]; then
            summary+="$name($verdict): $issues; "
        fi
    done
    
    if [[ -n "$summary" ]]; then
        mnemo remember "$tag: $summary" 2>/dev/null || true
    fi
}

# Recall past council findings for similar tasks
memory_recall() {
    local task="$1"
    if has_mnemo; then
        mnemo recall --tag "council" --query "$task" --limit 5 2>/dev/null || echo ""
    else
        echo ""
    fi
}
