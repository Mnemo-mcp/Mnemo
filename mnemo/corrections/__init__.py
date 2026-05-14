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


def _correction_similarity(a: str, b: str) -> float:
    """Simple token overlap similarity for corrections."""
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def add_correction(
    repo_root: Path,
    suggestion: str,
    correction: str,
    context: str = "",
    file: str = "",
) -> dict:
    """Store an AI suggestion that was corrected by the user."""
    corrections = _load_corrections(repo_root)

    # Check for similar existing correction — boost confidence instead of adding new
    for existing in corrections:
        sim = _correction_similarity(correction, existing.get("correction", ""))
        if sim > 0.7:
            existing["confidence"] = min(existing.get("confidence", 0.7) + 0.1, 1.0)
            _save_corrections(repo_root, corrections)
            return existing

    next_id = max((c.get("id", 0) for c in corrections), default=0) + 1
    entry = {
        "id": next_id,
        "timestamp": time.time(),
        "suggestion": suggestion,
        "correction": correction,
        "context": context,
        "file": file,
        "confidence": 0.7,
    }
    corrections.append(entry)
    _save_corrections(repo_root, corrections)

    # MNO-024: Decay confidence of memories matching this correction
    try:
        from ..storage import Collections, get_storage
        storage = get_storage(repo_root)
        memories = storage.read_collection(Collections.MEMORY)
        if isinstance(memories, list):
            search_text = (context + " " + suggestion).lower()
            changed = False
            for mem in memories:
                mc = mem.get("content", "").lower()
                if _correction_similarity(search_text, mc) > 0.5:
                    mem["confidence"] = max(mem.get("confidence", 0.8) - 0.1, 0.1)
                    changed = True
            if changed:
                storage.write_collection(Collections.MEMORY, memories)
    except Exception:
        pass

    return entry


def decay_corrections(repo_root: Path) -> None:
    """Decay all correction confidences by multiplying by 0.995."""
    corrections = _load_corrections(repo_root)
    if not corrections:
        return
    for c in corrections:
        c["confidence"] = c.get("confidence", 0.7) * 0.995
    _save_corrections(repo_root, corrections)


def get_corrections(repo_root: Path, query: str = "", limit: int = 20, offset: int = 0) -> str:
    """Get stored corrections, optionally filtered by query, with pagination."""
    corrections = _load_corrections(repo_root)
    if not corrections:
        return "No corrections stored."

    # Filter out low-confidence corrections
    corrections = [c for c in corrections if c.get("confidence", 0.7) >= 0.3]

    if query:
        query_lower = query.lower()
        corrections = [c for c in corrections if
                       query_lower in c.get("context", "").lower() or
                       query_lower in c.get("file", "").lower() or
                       query_lower in c.get("correction", "").lower()]

    if not corrections:
        return f"No corrections matching '{query}'." if query else "No corrections stored."

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
