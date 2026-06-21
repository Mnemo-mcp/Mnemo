"""Autorun orchestrator — chains workflow skills with quality gate enforcement.

Runs: investigate → plan → implement → verify → review → ship
Enforces gates between phases. Can resume from any point.
Stores phase state in .mnemo/autorun_state.json.

Usage:
    from mnemo.skills.orchestrator import get_phase_status, advance_phase, get_skill_for_phase

    # Check current state
    status = get_phase_status(repo_root)

    # Get the skill content for the current phase
    skill = get_skill_for_phase(status["current_phase"])

    # After a phase completes, try to advance
    result = advance_phase(repo_root)
    # Returns: {"advanced": True, "from": "verify", "to": "review"}
    # Or: {"advanced": False, "gate_failed": "tests_pass", "message": "Tests FAILED..."}
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from ..config import mnemo_path
from ..core.atomic import atomic_write_json, atomic_read_json
from ..quality.gates import check_gate
from . import WORKFLOW_SKILLS


# Phase order
PHASES = ["investigate", "plan", "implement", "verify", "review", "ship"]

# Gates required between phases (checked before advancing TO the target phase)
PHASE_GATES: dict[str, list[str]] = {
    "investigate": [],           # No gate to start investigating
    "plan": [],                  # No gate to start planning
    "implement": [],             # No gate to start implementing
    "verify": [],                # No gate to start verifying
    "review": ["tests_pass"],    # Tests must pass before review
    "ship": ["tests_pass", "plan_done", "no_findings"],  # All gates before shipping
}


def _state_path(repo_root: Path) -> Path:
    return mnemo_path(repo_root) / "autorun_state.json"


def get_phase_status(repo_root: Path) -> dict[str, Any]:
    """Get current autorun state.

    Returns:
        {
            "current_phase": "implement",
            "phase_index": 2,
            "started_at": <timestamp>,
            "phases_completed": ["investigate", "plan"],
            "total_phases": 6
        }
    """
    state = atomic_read_json(_state_path(repo_root), default={})
    if not state:
        return {
            "current_phase": None,
            "phase_index": -1,
            "started_at": None,
            "phases_completed": [],
            "total_phases": len(PHASES),
        }
    return state


def start_autorun(repo_root: Path, start_from: str = "investigate") -> dict[str, Any]:
    """Start or restart the autorun pipeline from a specific phase.

    Args:
        repo_root: Repository root.
        start_from: Phase to start from (default: investigate).

    Returns:
        Current state after starting.
    """
    if start_from not in PHASES:
        raise ValueError(f"Unknown phase: {start_from}. Valid: {', '.join(PHASES)}")

    idx = PHASES.index(start_from)
    completed = PHASES[:idx]  # Assume earlier phases are done if starting later

    state = {
        "current_phase": start_from,
        "phase_index": idx,
        "started_at": time.time(),
        "phases_completed": completed,
        "total_phases": len(PHASES),
    }
    atomic_write_json(_state_path(repo_root), state)
    return state


def advance_phase(repo_root: Path) -> dict[str, Any]:
    """Try to advance to the next phase. Checks gates first.

    Returns:
        On success: {"advanced": True, "from": "<phase>", "to": "<next>"}
        On gate failure: {"advanced": False, "gate_failed": "<gate>", "message": "<why>"}
        On completion: {"advanced": True, "from": "ship", "to": "done", "complete": True}
    """
    state = get_phase_status(repo_root)
    current = state.get("current_phase")

    if not current:
        return {"advanced": False, "gate_failed": "not_started", "message": "Autorun not started. Call start_autorun() first."}

    current_idx = PHASES.index(current)
    if current_idx >= len(PHASES) - 1:
        # We're on the last phase (ship) — completing means done
        completed = state.get("phases_completed", [])
        if current not in completed:
            completed.append(current)
        state["phases_completed"] = completed
        state["current_phase"] = "done"
        state["completed_at"] = time.time()
        atomic_write_json(_state_path(repo_root), state)
        return {"advanced": True, "from": current, "to": "done", "complete": True}

    next_phase = PHASES[current_idx + 1]

    # Check gates for the next phase
    gates = PHASE_GATES.get(next_phase, [])
    for gate in gates:
        passed, message = check_gate(repo_root, gate)
        if not passed:
            return {"advanced": False, "gate_failed": gate, "message": message}

    # All gates pass — advance
    completed = state.get("phases_completed", [])
    if current not in completed:
        completed.append(current)

    state["current_phase"] = next_phase
    state["phase_index"] = current_idx + 1
    state["phases_completed"] = completed
    atomic_write_json(_state_path(repo_root), state)

    return {"advanced": True, "from": current, "to": next_phase}


def get_skill_for_phase(phase: str) -> str | None:
    """Get the SKILL.md content for a given phase.

    Returns None if phase is not a valid skill phase (e.g., "done").
    """
    return WORKFLOW_SKILLS.get(phase)


def reset_autorun(repo_root: Path) -> None:
    """Clear autorun state (start fresh)."""
    path = _state_path(repo_root)
    if path.exists():
        path.unlink()


def format_status(repo_root: Path) -> str:
    """Format autorun status as human-readable string."""
    state = get_phase_status(repo_root)
    current = state.get("current_phase")
    completed = state.get("phases_completed", [])

    if not current:
        return "Autorun: not started. Run `/autorun` to begin."

    if current == "done":
        return "Autorun: ✅ COMPLETE. All phases finished."

    lines = ["# Autorun Pipeline Status", ""]
    for i, phase in enumerate(PHASES):
        if phase in completed:
            lines.append(f"  ✅ {phase}")
        elif phase == current:
            lines.append(f"  ▶️  {phase} ← CURRENT")
        else:
            gates = PHASE_GATES.get(phase, [])
            gate_str = f" (gates: {', '.join(gates)})" if gates else ""
            lines.append(f"  ⬜ {phase}{gate_str}")

    return "\n".join(lines)
