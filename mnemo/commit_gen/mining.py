"""Mine git commit messages for decision-like content (MNO-839)."""

from __future__ import annotations

import re
from pathlib import Path

_DECISION_SIGNALS = re.compile(
    r'\b(migrat|refactor|replac|switch|adopt|introduc|remov|deprecat|upgrad|redesign|restructur)',
    re.I,
)

_SKIP_PREFIXES = ("merge ", "wip", "fix typo", "update readme", "bump version")


def mine_commits_for_decisions(repo_root: Path, limit: int = 50) -> list[dict[str, str]]:
    """Scan recent git commits for decision-like messages."""
    try:
        import git
        repo = git.Repo(repo_root)
    except Exception:
        return []

    decisions = []
    for commit in list(repo.iter_commits(max_count=limit)):
        msg = commit.message.strip().split("\n")[0]  # First line only
        if len(msg) < 15:
            continue
        if any(msg.lower().startswith(p) for p in _SKIP_PREFIXES):
            continue
        if _DECISION_SIGNALS.search(msg):
            decisions.append({
                "message": msg,
                "author": str(commit.author),
                "date": commit.committed_datetime.isoformat()[:10],
            })

    return decisions


def auto_store_commit_decisions(repo_root: Path, limit: int = 50) -> str:
    """Mine commits and store new decisions that aren't already known."""
    from .memory import add_decision, _text_similarity
    from .storage import Collections, get_storage

    mined = mine_commits_for_decisions(repo_root, limit)
    if not mined:
        return "No decision-like commits found."

    storage = get_storage(repo_root)
    existing = storage.read_collection(Collections.DECISIONS)
    existing_texts = [d.get("decision", "").lower() for d in existing if isinstance(d, dict)]

    stored = 0
    for commit in mined:
        msg = commit["message"]
        # Skip if already stored
        if any(_text_similarity(msg, e) > 0.7 for e in existing_texts):
            continue
        add_decision(repo_root, msg, reasoning=f"From git commit by {commit['author']} on {commit['date']}")
        existing_texts.append(msg.lower())
        stored += 1

    return f"Mined {len(mined)} decision-like commits, stored {stored} new decisions."
