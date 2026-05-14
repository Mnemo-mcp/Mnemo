"""Memory service layer — orchestrates side effects around memory mutations."""

from __future__ import annotations

import time
from pathlib import Path

from .store import add_memory, add_decision, _auto_categorize
from ..plan import auto_create_plan_from_text
from ..retrieval import semantic_query
from ..storage import Collections, get_storage

# Consolidation runs at most once per hour
_CONSOLIDATION_COOLDOWN = 3600
_last_consolidation: float = 0
_CONSOLIDATION_THRESHOLD = 80  # Trigger when memory count exceeds this


def remember_with_effects(repo_root: Path, content: str, category: str = "general") -> str:
    """Store memory and trigger plan auto-creation + similar bug detection + auto-consolidation."""
    entry = add_memory(repo_root, content, category, source="user")
    result = f"Stored memory #{entry['id']}: {entry['content']}"

    plan_result = auto_create_plan_from_text(repo_root, content, source="memory")
    if plan_result:
        result += f"\n\n{plan_result}"

    if _auto_categorize(content) == "bug":
        hits = semantic_query(repo_root, "code", content, limit=3)
        if hits:
            result += "\n\n⚠️ **Similar code found** (may have same issue):"
            for h in hits:
                meta = h.get("metadata", {})
                result += f"\n- `{meta.get('path', '')}` :: `{meta.get('symbol', '')}`"

    # Auto-consolidation: merge similar memories when count gets high
    _maybe_consolidate(repo_root)

    return result


def _maybe_consolidate(repo_root: Path) -> None:
    """Run consolidation if memory count exceeds threshold and cooldown has passed."""
    global _last_consolidation
    now = time.time()
    if now - _last_consolidation < _CONSOLIDATION_COOLDOWN:
        return

    storage = get_storage(repo_root)
    entries = storage.read_collection(Collections.MEMORY)
    if not isinstance(entries, list):
        return

    active = [e for e in entries if not e.get("evicted") and not e.get("superseded_by")]
    if len(active) < _CONSOLIDATION_THRESHOLD:
        return

    _last_consolidation = now

    from .retention import compress_memory
    try:
        compress_memory(repo_root)
    except Exception:
        pass


def decide_with_effects(repo_root: Path, decision: str, reasoning: str = "") -> str:
    """Record decision and trigger plan auto-creation."""
    entry = add_decision(repo_root, decision, reasoning)
    result = f"Decision #{entry['id']} recorded: {entry['decision']}"

    superseded = entry.pop("_superseded", None)
    if superseded:
        for s in superseded:
            result += f"\n⚠️ Superseded decision #{s['id']}: {s['decision']}"

    combined = f"{decision}\n{reasoning}"
    plan_result = auto_create_plan_from_text(repo_root, combined, source="decision")
    if plan_result:
        result += f"\n\n{plan_result}"

    return result
