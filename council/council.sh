#!/bin/bash
# ABOUTME: Main council orchestrator — detects phase, spawns evaluators, runs GAN loop
set -euo pipefail

COUNCIL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${COUNCIL_DIR}/lib/common.sh"
source "${COUNCIL_DIR}/lib/phases.sh"
source "${COUNCIL_DIR}/lib/memory.sh"

usage() {
    cat >&2 << 'EOF'
Usage: council.sh [OPTIONS] -- <task description>

Options:
  --phase PHASE       Force phase (plan|implement|test|review|debug)
  --max-iter N        Max GAN loop iterations (default: 3)
  --file PATH         Include file context
  --spec PATH         Existing spec file to use
  --no-memory         Skip mnemo memory queries
  --verbose           Show evaluator details

Phases auto-detected from task if not specified.
EOF
    exit 1
}

# Parse args
PHASE=""
MAX_ITER=3
FILE_CONTEXT=""
SPEC_FILE=""
USE_MEMORY=true
VERBOSE=false
TASK=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --phase) PHASE="$2"; shift 2 ;;
        --phase=*) PHASE="${1#*=}"; shift ;;
        --max-iter) MAX_ITER="$2"; shift 2 ;;
        --max-iter=*) MAX_ITER="${1#*=}"; shift ;;
        --file) FILE_CONTEXT="$2"; shift 2 ;;
        --file=*) FILE_CONTEXT="${1#*=}"; shift ;;
        --spec) SPEC_FILE="$2"; shift 2 ;;
        --spec=*) SPEC_FILE="${1#*=}"; shift ;;
        --no-memory) USE_MEMORY=false; shift ;;
        --verbose) VERBOSE=true; shift ;;
        --) shift; TASK="$*"; break ;;
        -*) usage ;;
        *) TASK="$*"; break ;;
    esac
done

[[ -z "$TASK" ]] && usage

# Phase detection
if [[ -z "$PHASE" ]]; then
    PHASE=$(detect_phase "$TASK")
fi
log "Phase: $PHASE"

# Memory context (optional)
MEMORY_CONTEXT=""
if [[ "$USE_MEMORY" == true ]]; then
    MEMORY_CONTEXT=$(memory_query "$TASK")
fi

# File context
CODE_CONTEXT=""
if [[ -n "$FILE_CONTEXT" && -f "$FILE_CONTEXT" ]]; then
    CODE_CONTEXT=$(cat "$FILE_CONTEXT")
fi

# Load phase config
EVALUATORS=$(get_phase_evaluators "$PHASE")
HAS_LOOP=$(get_phase_loop "$PHASE")

# --- PLAN PHASE (advisory, no loop) ---
if [[ "$PHASE" == "plan" || "$HAS_LOOP" == "false" ]]; then
    log "Running advisory council ($PHASE)..."
    
    RESULTS_DIR=$(mktemp -d)
    trap "rm -rf $RESULTS_DIR" EXIT
    
    # Spawn evaluators in parallel
    for eval_name in $EVALUATORS; do
        "${COUNCIL_DIR}/evaluators/${eval_name}.sh" \
            "$TASK" "$CODE_CONTEXT" "$MEMORY_CONTEXT" "$SPEC_FILE" \
            > "${RESULTS_DIR}/${eval_name}.json" 2>/dev/null &
    done
    wait
    
    # Synthesize
    "${COUNCIL_DIR}/synthesize.sh" "$PHASE" "$RESULTS_DIR"
    
    # Store to memory
    if [[ "$USE_MEMORY" == true ]]; then
        memory_store "council-$PHASE" "$RESULTS_DIR"
    fi
    exit 0
fi

# --- GAN LOOP PHASES (implement, test, debug) ---
log "Running GAN loop ($PHASE, max $MAX_ITER iterations)..."

ITERATION=0
FEEDBACK=""

while [[ $ITERATION -lt $MAX_ITER ]]; do
    ITERATION=$((ITERATION + 1))
    log "=== Iteration $ITERATION/$MAX_ITER ==="
    
    RESULTS_DIR=$(mktemp -d)
    
    # Generate (or re-generate with feedback)
    GENERATOR_OUTPUT=$("${COUNCIL_DIR}/generate.sh" \
        "$TASK" "$CODE_CONTEXT" "$MEMORY_CONTEXT" "$SPEC_FILE" "$FEEDBACK")
    
    # Spawn evaluators in parallel
    for eval_name in $EVALUATORS; do
        "${COUNCIL_DIR}/evaluators/${eval_name}.sh" \
            "$TASK" "$GENERATOR_OUTPUT" "$MEMORY_CONTEXT" "$SPEC_FILE" \
            > "${RESULTS_DIR}/${eval_name}.json" 2>/dev/null &
    done
    wait
    
    # Collect verdicts
    VERDICT=$(collect_verdicts "$RESULTS_DIR")
    
    case "$VERDICT" in
        PASS)
            log "✅ All evaluators passed at iteration $ITERATION"
            "${COUNCIL_DIR}/synthesize.sh" "$PHASE" "$RESULTS_DIR"
            if [[ "$USE_MEMORY" == true ]]; then
                memory_store "council-$PHASE-pass" "$RESULTS_DIR"
            fi
            rm -rf "$RESULTS_DIR"
            exit 0
            ;;
        REPLAN)
            log "🔄 Replan triggered at iteration $ITERATION"
            REPLAN_REASON=$(get_replan_reason "$RESULTS_DIR")
            echo "REPLAN: $REPLAN_REASON"
            if [[ "$USE_MEMORY" == true ]]; then
                memory_store "council-replan" "$RESULTS_DIR"
            fi
            rm -rf "$RESULTS_DIR"
            exit 2  # Exit code 2 = replan needed
            ;;
        FAIL)
            FEEDBACK=$(collect_feedback "$RESULTS_DIR")
            log "❌ Iteration $ITERATION failed. Feedback collected."
            [[ "$VERBOSE" == true ]] && echo "$FEEDBACK"
            ;;
    esac
    
    rm -rf "$RESULTS_DIR"
done

# Max iterations reached
log "⚠️  Max iterations ($MAX_ITER) reached without all-pass."
echo "INCOMPLETE: Evaluators did not fully pass after $MAX_ITER iterations."
echo "Last feedback: $FEEDBACK"
exit 1
