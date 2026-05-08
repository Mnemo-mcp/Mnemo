"""Error Memory — store error → cause → fix mappings for instant recall."""

from __future__ import annotations

import json
import time
from pathlib import Path

from ..config import mnemo_path

ERRORS_FILE = "errors.json"


def _errors_path(repo_root: Path) -> Path:
    return mnemo_path(repo_root) / ERRORS_FILE


def _load_errors(repo_root: Path) -> list[dict]:
    path = _errors_path(repo_root)
    if path.exists():
        return json.loads(path.read_text())
    return []


def _save_errors(repo_root: Path, errors: list[dict]):
    _errors_path(repo_root).write_text(json.dumps(errors[-200:], indent=2))


def add_error(repo_root: Path, error: str, cause: str, fix: str,
              file: str = "", tags: list[str] = None) -> dict:
    """Store an error → cause → fix mapping."""
    errors = _load_errors(repo_root)
    entry = {
        "id": len(errors) + 1,
        "timestamp": time.time(),
        "error": error,
        "cause": cause,
        "fix": fix,
        "file": file,
        "tags": tags or [],
    }
    errors.append(entry)
    _save_errors(repo_root, errors)
    return entry


def search_errors(repo_root: Path, query: str) -> str:
    """Search error memory for matching errors."""
    errors = _load_errors(repo_root)
    query_lower = query.lower()

    matches = [e for e in errors if
               query_lower in e["error"].lower() or
               query_lower in e.get("cause", "").lower() or
               query_lower in e.get("file", "").lower() or
               any(query_lower in t.lower() for t in e.get("tags", []))]

    if not matches:
        return f"No known errors matching '{query}'."

    lines = [f"# Known Errors matching '{query}'\n"]
    for e in matches[-10:]:
        lines.append(f"## {e['error']}")
        lines.append(f"**Cause:** {e['cause']}")
        lines.append(f"**Fix:** {e['fix']}")
        if e.get("file"):
            lines.append(f"**File:** {e['file']}")
        lines.append("")
    return "\n".join(lines)


def format_errors(repo_root: Path) -> str:
    """Format all stored errors as markdown."""
    errors = _load_errors(repo_root)
    if not errors:
        return "No errors stored."

    lines = ["# Error Memory\n"]
    for e in errors[-20:]:
        lines.append(f"- **{e['error']}** → {e['fix']}")
    return "\n".join(lines)
