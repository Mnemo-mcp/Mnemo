"""Error memory - store error, cause, and fix mappings for instant recall."""

from __future__ import annotations

import time
from pathlib import Path

from ..storage import Collections, get_storage


def _load_errors(repo_root: Path) -> list[dict]:
    data = get_storage(repo_root).read_collection(Collections.ERRORS)
    return data if isinstance(data, list) else []


def _save_errors(repo_root: Path, errors: list[dict]) -> None:
    get_storage(repo_root).write_collection(Collections.ERRORS, errors[-200:])


def add_error(
    repo_root: Path,
    error: str,
    cause: str,
    fix: str,
    file: str = "",
    tags: list[str] | None = None,
) -> dict:
    """Store an error, cause, and fix mapping."""
    errors = _load_errors(repo_root)
    next_id = max((e.get("id", 0) for e in errors), default=0) + 1
    entry = {
        "id": next_id,
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

    matches = [
        error
        for error in errors
        if query_lower in error["error"].lower()
        or query_lower in error.get("cause", "").lower()
        or query_lower in error.get("file", "").lower()
        or any(query_lower in tag.lower() for tag in error.get("tags", []))
    ]

    if not matches:
        return f"No known errors matching '{query}'."

    lines = [f"# Known Errors matching '{query}'\n"]
    for error in matches[-10:]:
        lines.append(f"## {error['error']}")
        lines.append(f"**Cause:** {error['cause']}")
        lines.append(f"**Fix:** {error['fix']}")
        if error.get("file"):
            lines.append(f"**File:** {error['file']}")
        lines.append("")
    return "\n".join(lines)


def format_errors(repo_root: Path) -> str:
    """Format all stored errors as markdown."""
    errors = _load_errors(repo_root)
    if not errors:
        return "No errors stored."

    lines = ["# Error Memory\n"]
    for error in errors[-20:]:
        lines.append(f"- **{error['error']}** -> {error['fix']}")
    return "\n".join(lines)
