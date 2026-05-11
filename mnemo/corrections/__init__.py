"""Learning from corrections - store AI suggestion vs user correction pairs."""

from __future__ import annotations

import json
import time
from pathlib import Path

from ..config import mnemo_path

STORAGE_FILE = "corrections.json"


def _load_corrections(repo_root: Path) -> list[dict]:
    path = mnemo_path(repo_root) / STORAGE_FILE
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_corrections(repo_root: Path, data: list[dict]) -> None:
    path = mnemo_path(repo_root) / STORAGE_FILE
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def add_correction(
    repo_root: Path,
    suggestion: str,
    correction: str,
    context: str = "",
    file: str = "",
) -> dict:
    """Store an AI suggestion that was corrected by the user."""
    corrections = _load_corrections(repo_root)
    next_id = max((c.get("id", 0) for c in corrections), default=0) + 1
    entry = {
        "id": next_id,
        "timestamp": time.time(),
        "suggestion": suggestion,
        "correction": correction,
        "context": context,
        "file": file,
    }
    corrections.append(entry)
    _save_corrections(repo_root, corrections)
    return entry


def get_corrections(repo_root: Path, query: str = "", limit: int = 20, offset: int = 0) -> str:
    """Get stored corrections, optionally filtered by query, with pagination."""
    corrections = _load_corrections(repo_root)
    if not corrections:
        return "No corrections stored."

    if query:
        query_lower = query.lower()
        corrections = [c for c in corrections if
                       query_lower in c.get("context", "").lower() or
                       query_lower in c.get("file", "").lower() or
                       query_lower in c.get("correction", "").lower()]

    if not corrections:
        return f"No corrections matching '{query}'."

    total = len(corrections)
    page = corrections[offset:offset + limit]

    lines = [f"# Learned Corrections ({total} total)\n"]
    for c in page:
        lines.append(f"- **Wrong:** {c['suggestion'][:80]}")
        lines.append(f"  **Right:** {c['correction'][:80]}")
        if c.get("context"):
            lines.append(f"  *Context:* {c['context'][:60]}")
        lines.append("")
    if total > offset + limit:
        lines.append(f"*Showing {len(page)} of {total}. Use offset={offset + limit} for more.*")
    return "\n".join(lines)
