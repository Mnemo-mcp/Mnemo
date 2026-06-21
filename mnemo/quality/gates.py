"""Quality gates — conditions that must pass between workflow phases.

Each gate returns (passed: bool, message: str).
Gates are called by skills to verify preconditions before proceeding.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ..config import mnemo_path
from ..plan import _load_plans


def check_gate(repo_root: Path, gate: str) -> tuple[bool, str]:
    """Check a named quality gate. Returns (passed, message).

    Gates:
        tests_pass   — run test suite, verify exit 0
        plan_done    — all plan tasks marked done
        no_findings  — no unresolved critical review findings
    """
    gates = {
        "tests_pass": _gate_tests_pass,
        "plan_done": _gate_plan_done,
        "no_findings": _gate_no_findings,
    }
    fn = gates.get(gate)
    if not fn:
        return False, f"Unknown gate: {gate}"
    return fn(repo_root)


def check_all_gates(repo_root: Path) -> list[tuple[str, bool, str]]:
    """Check all gates. Returns list of (gate_name, passed, message)."""
    results = []
    for gate in ("tests_pass", "plan_done", "no_findings"):
        passed, msg = check_gate(repo_root, gate)
        results.append((gate, passed, msg))
    return results


def _gate_tests_pass(repo_root: Path) -> tuple[bool, str]:
    """Run test suite and verify it passes."""
    # Detect test runner
    if (repo_root / "pytest.ini").exists() or (repo_root / "pyproject.toml").exists():
        cmd = ["python", "-m", "pytest", "--tb=no", "-q"]
    elif (repo_root / "package.json").exists():
        cmd = ["npm", "test"]
    elif (repo_root / "pom.xml").exists():
        cmd = ["mvn", "test", "-q"]
    elif (repo_root / "build.gradle").exists() or (repo_root / "build.gradle.kts").exists():
        cmd = ["./gradlew", "test", "--quiet"]
    else:
        return True, "No test runner detected — gate skipped"

    try:
        result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            return True, "Tests pass ✅"
        # Extract failure summary
        output = (result.stdout + result.stderr)[-500:]
        return False, f"Tests FAILED ❌\n{output}"
    except subprocess.TimeoutExpired:
        return False, "Tests timed out (300s limit)"
    except FileNotFoundError:
        return True, f"Test runner not found ({cmd[0]}) — gate skipped"


def _gate_plan_done(repo_root: Path) -> tuple[bool, str]:
    """Check that all tasks in the active plan are marked done."""
    plans = _load_plans(repo_root)
    active = [p for p in plans if p.get("status") in (None, "active", "in_progress")]
    if not active:
        return True, "No active plan — gate skipped"

    plan = active[-1]
    tasks = plan.get("tasks", [])
    if not tasks:
        return True, "Plan has no tasks — gate skipped"

    done = [t for t in tasks if t.get("status") == "done"]
    pending = [t for t in tasks if t.get("status") != "done"]

    if not pending:
        return True, f"All {len(done)} tasks done ✅"

    pending_titles = [t.get("title", t.get("description", "?"))[:50] for t in pending[:3]]
    return False, f"Plan incomplete ❌ — {len(pending)}/{len(tasks)} pending: {', '.join(pending_titles)}"


def _gate_no_findings(repo_root: Path) -> tuple[bool, str]:
    """Check that no unresolved critical findings exist."""
    findings_path = mnemo_path(repo_root) / "review_findings.json"
    if not findings_path.exists():
        return True, "No review findings file — gate skipped"

    import json
    try:
        findings = json.loads(findings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return True, "Could not read findings — gate skipped"

    if not isinstance(findings, list):
        return True, "No findings"

    critical = [f for f in findings if f.get("severity") in ("critical", "high") and not f.get("resolved")]
    if not critical:
        return True, f"No unresolved critical findings ✅ ({len(findings)} total, all resolved)"

    summaries = [f.get("summary", "?")[:60] for f in critical[:3]]
    return False, f"{len(critical)} unresolved critical findings ❌: {'; '.join(summaries)}"
