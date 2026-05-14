"""Memory service layer — orchestrates side effects around memory mutations."""

from __future__ import annotations

from pathlib import Path

from .store import add_memory, add_decision, _auto_categorize
from ..plan import auto_create_plan_from_text
from ..retrieval import semantic_query


def remember_with_effects(repo_root: Path, content: str, category: str = "general") -> str:
    """Store memory and trigger plan auto-creation + similar bug detection."""
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

    return result


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
