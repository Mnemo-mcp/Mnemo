"""Memory Hierarchy — tiered memory with working/session/persistent/episodic layers (MNO-811-813)."""

from __future__ import annotations

import time
from pathlib import Path


# Tier definitions
TIERS = ("working", "session", "persistent", "episodic")

# TTL in seconds (0 = permanent)
TIER_TTL = {
    "working": 4 * 3600,       # 4 hours
    "session": 7 * 24 * 3600,  # 7 days
    "persistent": 0,           # permanent
    "episodic": 0,             # permanent (historical)
}

# Categories that map to specific tiers
CATEGORY_TIER_MAP = {
    "architecture": "persistent",
    "preference": "persistent",
    "decision": "persistent",
    "bug": "episodic",
    "pattern": "persistent",
    "todo": "session",
    "general": "session",
}


def assign_tier(category: str, content: str) -> str:
    """Auto-assign a memory to the appropriate tier based on category and content."""
    # Explicit tier from category
    tier = CATEGORY_TIER_MAP.get(category, "session")

    # Promote to persistent if content has strong signals
    persistent_signals = ("always", "never", "convention", "architecture", "decided", "standard")
    if tier == "session" and any(s in content.lower() for s in persistent_signals):
        tier = "persistent"

    # Demote to working if content is very short/transient
    if len(content) < 20 and tier == "session":
        tier = "working"

    return tier


def expire_working_memory(repo_root: Path) -> int:
    """Remove expired working memory entries. Returns count removed."""
    from ..storage import Collections, get_storage
    storage = get_storage(repo_root)
    entries = storage.read_collection(Collections.MEMORY)
    if not isinstance(entries, list):
        return 0

    now = time.time()
    before = len(entries)
    entries = [
        e for e in entries
        if not (e.get("tier") == "working" and now - e.get("timestamp", now) > TIER_TTL["working"])
    ]
    removed = before - len(entries)
    if removed > 0:
        storage.write_collection(Collections.MEMORY, entries)
    return removed


def expire_session_memory(repo_root: Path) -> int:
    """Archive expired session memory entries. Returns count archived."""
    from ..storage import Collections, get_storage
    storage = get_storage(repo_root)
    entries = storage.read_collection(Collections.MEMORY)
    if not isinstance(entries, list):
        return 0

    now = time.time()
    active = []
    archived = 0
    for e in entries:
        if e.get("tier") == "session" and now - e.get("timestamp", now) > TIER_TTL["session"]:
            # Don't delete — just mark as archived if recall_count is low
            if e.get("recall_count", 0) < 2:
                e["tier"] = "archived"
                archived += 1
            else:
                # Promote frequently-recalled session memories to persistent
                e["tier"] = "persistent"
        active.append(e)

    if archived > 0:
        storage.write_collection(Collections.MEMORY, active)
    return archived


def get_tier_stats(repo_root: Path) -> dict[str, int]:
    """Get count of memories per tier."""
    from ..storage import Collections, get_storage
    storage = get_storage(repo_root)
    entries = storage.read_collection(Collections.MEMORY)
    if not isinstance(entries, list):
        return {}

    stats: dict[str, int] = {}
    for e in entries:
        tier = e.get("tier", "session")
        stats[tier] = stats.get(tier, 0) + 1
    return stats
