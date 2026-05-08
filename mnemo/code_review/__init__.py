"""Code Review Context — store PR summaries, review feedback, rejected suggestions."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ..config import mnemo_path

REVIEWS_FILE = "reviews.json"


def _reviews_path(repo_root: Path) -> Path:
    return mnemo_path(repo_root) / REVIEWS_FILE


def _load_reviews(repo_root: Path) -> list[dict]:
    path = _reviews_path(repo_root)
    if path.exists():
        return json.loads(path.read_text())
    return []


def _save_reviews(repo_root: Path, reviews: list[dict]):
    _reviews_path(repo_root).write_text(json.dumps(reviews[-100:], indent=2))


def add_review(repo_root: Path, summary: str, files: list[str] = None,
               feedback: str = "", outcome: str = "approved") -> dict:
    """Store a code review summary."""
    reviews = _load_reviews(repo_root)
    entry = {
        "id": len(reviews) + 1,
        "timestamp": time.time(),
        "summary": summary,
        "files": files or [],
        "feedback": feedback,
        "outcome": outcome,  # approved, rejected, changes_requested
    }
    reviews.append(entry)
    _save_reviews(repo_root, reviews)
    return entry


def get_reviews_for_file(repo_root: Path, filepath: str) -> list[dict]:
    """Get all review feedback related to a specific file."""
    reviews = _load_reviews(repo_root)
    return [r for r in reviews if filepath in (r.get("files") or [])]


def get_rejected_suggestions(repo_root: Path) -> list[dict]:
    """Get suggestions that were rejected — Q should not repeat these."""
    reviews = _load_reviews(repo_root)
    return [r for r in reviews if r.get("outcome") == "rejected"]


def format_reviews(repo_root: Path) -> str:
    """Format review history as markdown."""
    reviews = _load_reviews(repo_root)
    if not reviews:
        return "No code review history stored."

    lines = ["# Code Review History\n"]
    for r in reviews[-20:]:
        status = f"[{r['outcome']}]" if r.get("outcome") else ""
        lines.append(f"- {r['summary']} {status}")
        if r.get("feedback"):
            lines.append(f"  Feedback: {r['feedback']}")
        if r.get("files"):
            lines.append(f"  Files: {', '.join(r['files'])}")
    return "\n".join(lines)
