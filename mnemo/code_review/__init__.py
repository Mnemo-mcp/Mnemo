"""Code review context - store PR summaries, feedback, and rejected suggestions."""

from __future__ import annotations

import time
from pathlib import Path

from ..storage import Collections, get_storage


def _load_reviews(repo_root: Path) -> list[dict]:
    data = get_storage(repo_root).read_collection(Collections.REVIEWS)
    return data if isinstance(data, list) else []


def _save_reviews(repo_root: Path, reviews: list[dict]) -> None:
    get_storage(repo_root).write_collection(Collections.REVIEWS, reviews[-100:])


def add_review(
    repo_root: Path,
    summary: str,
    files: list[str] | None = None,
    feedback: str = "",
    outcome: str = "approved",
) -> dict:
    """Store a code review summary."""
    reviews = _load_reviews(repo_root)
    entry = {
        "id": len(reviews) + 1,
        "timestamp": time.time(),
        "summary": summary,
        "files": files or [],
        "feedback": feedback,
        "outcome": outcome,
    }
    reviews.append(entry)
    _save_reviews(repo_root, reviews)
    return entry


def get_reviews_for_file(repo_root: Path, filepath: str) -> list[dict]:
    """Get all review feedback related to a specific file."""
    reviews = _load_reviews(repo_root)
    return [review for review in reviews if filepath in (review.get("files") or [])]


def get_rejected_suggestions(repo_root: Path) -> list[dict]:
    """Get suggestions that were rejected so assistants should not repeat them."""
    reviews = _load_reviews(repo_root)
    return [review for review in reviews if review.get("outcome") == "rejected"]


def format_reviews(repo_root: Path) -> str:
    """Format review history as markdown."""
    reviews = _load_reviews(repo_root)
    if not reviews:
        return "No code review history stored."

    lines = ["# Code Review History\n"]
    for review in reviews[-20:]:
        status = f"[{review['outcome']}]" if review.get("outcome") else ""
        lines.append(f"- {review['summary']} {status}")
        if review.get("feedback"):
            lines.append(f"  Feedback: {review['feedback']}")
        if review.get("files"):
            lines.append(f"  Files: {', '.join(review['files'])}")
    return "\n".join(lines)
