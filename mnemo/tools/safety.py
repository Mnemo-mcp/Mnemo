"""Safety & Quality tools."""

from __future__ import annotations

import json
from pathlib import Path

from ..tool_registry import tool


@tool("mnemo_check_security",
      "Scan codebase for security issues (hardcoded secrets, SQL injection, eval, shell injection). Optionally scope to a single file.",
      properties={"file": {"type": "string", "description": "Optional file path to scope scan"}})
def _check_security(root: Path, args: dict) -> str:
    from ..security import check_security
    return check_security(root, args.get("file", ""))


@tool("mnemo_add_security_pattern",
      "Add a custom security pattern to watch for in code scans.",
      properties={
          "name": {"type": "string", "description": "Pattern name"},
          "regex": {"type": "string", "description": "Regex to match unsafe code"},
          "severity": {"type": "string", "description": "low, medium, or high"},
          "description": {"type": "string"},
      },
      required=["name", "regex"])
def _add_security_pattern(root: Path, args: dict) -> str:
    from ..security import add_security_pattern
    entry = add_security_pattern(root, args["name"], args["regex"],
                                 args.get("severity", "medium"), args.get("description", ""))
    return f"Security pattern #{entry['id']} added: {entry['name']}"


@tool("mnemo_breaking_changes",
      "Detect breaking changes by comparing current public API against saved baseline. Use action='baseline' to save current state.",
      properties={"action": {"type": "string", "description": "'check' (default) to detect changes, 'baseline' to save current API as baseline"}})
def _breaking_changes(root: Path, args: dict) -> str:
    from ..breaking import detect_breaking_changes, save_baseline
    if args.get("action") == "baseline":
        return save_baseline(root)
    return detect_breaking_changes(root)


@tool("mnemo_add_regression",
      "Record a regression risk for a file — links a past bug to a file path.",
      properties={
          "file": {"type": "string", "description": "File path with regression risk"},
          "bug": {"type": "string", "description": "What the bug was"},
          "fix": {"type": "string", "description": "How it was fixed"},
          "test": {"type": "string", "description": "Test that covers this"},
      },
      required=["file", "bug", "fix"])
def _add_regression(root: Path, args: dict) -> str:
    from ..regressions import add_regression
    entry = add_regression(root, args["file"], args["bug"], args["fix"], args.get("test", ""))
    return f"Regression #{entry['id']} recorded for {entry['file']}"


@tool("mnemo_check_regressions",
      "Check if a file has known regression risks. Without a file, lists all regressions.",
      properties={"file": {"type": "string", "description": "File to check (omit to list all)"}})
def _check_regressions(root: Path, args: dict) -> str:
    from ..regressions import check_regressions, list_regressions
    file = args.get("file", "")
    return check_regressions(root, file) if file else list_regressions(root)


@tool("mnemo_drift",
      "Detect architecture drift — compare current code patterns against stored architectural decisions.")
def _drift(root: Path, args: dict) -> str:
    from ..drift import detect_drift
    return detect_drift(root)


@tool("mnemo_check_conventions",
      "Check code against detected project conventions (naming, structure, patterns). Use action='detect' to re-scan conventions, or omit to validate.",
      properties={
          "file": {"type": "string", "description": "Optional file path to scope check"},
          "action": {"type": "string", "description": "'detect' to re-scan conventions, omit to check violations"},
      })
def _check_conventions(root: Path, args: dict) -> str:
    from ..conventions import detect_conventions, check_conventions
    if args.get("action") == "detect":
        conventions = detect_conventions(root)
        return f"# Detected Conventions\n\n```json\n{json.dumps(conventions, indent=2)}\n```"
    return check_conventions(root, args.get("file", ""))


@tool("mnemo_dead_code",
      "Detect potentially unused classes, methods, and functions in the codebase. Reports symbols only referenced in their definition file.")
def _dead_code(root: Path, args: dict) -> str:
    from ..dead_code import detect_dead_code
    return detect_dead_code(root)


@tool("mnemo_health",
      "Code health report — complexity hotspots, large files, potential god classes.")
def _health(root: Path, args: dict) -> str:
    from ..health import calculate_health
    return calculate_health(root)
