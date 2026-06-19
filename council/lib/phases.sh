#!/bin/bash
# ABOUTME: Phase detection and configuration
set -euo pipefail

COUNCIL_DIR="${COUNCIL_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

detect_phase() {
    local task="$1"
    local lower=$(echo "$task" | tr '[:upper:]' '[:lower:]')
    
    # Debug signals
    if echo "$lower" | grep -qE '(bug|fix|broken|failing|error|500|doesn.t work|investigate|crash)'; then
        echo "debug"; return
    fi
    # Review signals
    if echo "$lower" | grep -qE '(review|pr |pull request|check this|audit)'; then
        echo "review"; return
    fi
    # Test signals
    if echo "$lower" | grep -qE '(test|coverage|validate|verify|spec)'; then
        echo "test"; return
    fi
    # Plan signals
    if echo "$lower" | grep -qE '(design|architect|how should|approach|strategy|structure|plan)'; then
        echo "plan"; return
    fi
    # Default: implement
    echo "implement"
}

get_phase_evaluators() {
    local phase="$1"
    case "$phase" in
        plan)      echo "drift security innovation" ;;
        implement) echo "drift adversarial security realworld" ;;
        test)      echo "drift adversarial realworld" ;;
        review)    echo "security adversarial innovation" ;;
        debug)     echo "adversarial drift realworld" ;;
        *)         echo "drift adversarial security" ;;
    esac
}

get_phase_loop() {
    local phase="$1"
    case "$phase" in
        plan)      echo "false" ;;
        implement) echo "true" ;;
        test)      echo "true" ;;
        review)    echo "false" ;;
        debug)     echo "true" ;;
        *)         echo "false" ;;
    esac
}
