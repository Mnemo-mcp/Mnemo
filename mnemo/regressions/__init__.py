"""Regression memory - link file paths to past bugs for auto-checking."""

from __future__ import annotations

import json
import time
from pathlib import Path

from ..config import mnemo_path

STORAGE_FILE = "regressions.json"


def _load_regressions(repo_root: Path) -> list[dict]:
    path = mnemo_path(repo_root) / STORAGE_FILE
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_regressions(repo_root: Path, data: list[dict]) -> None:
    path = mnemo_path(repo_root) / STORAGE_FILE
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def add_regression(
    repo_root: Path,
    file: str,
    bug_description: str,
    fix_description: str,
    test: str = "",
) -> dict:
    """Record a regression risk for a file."""
    regressions = _load_regressions(repo_root)
    next_id = max((r.get("id", 0) for r in regressions), default=0) + 1
    entry = {
        "id": next_id,
        "timestamp": time.time(),
        "file": file,
        "bug": bug_description,
        "fix": fix_description,
        "test": test,
    }
    regressions.append(entry)
    _save_regressions(repo_root, regressions)
    return entry


def check_regressions(repo_root: Path, file: str) -> str:
    """Check if a file has known regression risks."""
    regressions = _load_regressions(repo_root)
    file_lower = file.lower()

    matches = [r for r in regressions if file_lower in r.get("file", "").lower()]

    if not matches:
        return f"No known regressions for `{file}`."

    lines = [f"# ⚠️ Regression Risks for `{file}` ({len(matches)} known)\n"]
    for r in matches:
        lines.append(f"## Bug: {r['bug']}")
        lines.append(f"**Fix:** {r['fix']}")
        if r.get("test"):
            lines.append(f"**Test:** {r['test']}")
        lines.append("")

    lines.append("*Be careful modifying this file — it has regressed before.*")
    return "\n".join(lines)


def list_regressions(repo_root: Path) -> str:
    """List all known regression risks."""
    regressions = _load_regressions(repo_root)
    if not regressions:
        return "No regressions recorded."

    lines = ["# Regression Memory\n"]
    for r in regressions:
        lines.append(f"- **{r['file']}**: {r['bug']} → {r['fix']}")
    return "\n".join(lines)
