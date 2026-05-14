"""Memory retention scoring, compression, and eviction."""

from __future__ import annotations

import math
import re
import time
from pathlib import Path
from typing import Any

from ..storage import Collections, get_storage
from ..utils.audit import record_audit

from ._shared import (
    COMPRESS_THRESHOLD,
    PINNED_CATEGORIES,
    _as_list,
    _next_id,
    _text_similarity,
    _refresh_rule,
)


def _compute_retention(entry: dict, now: float) -> float:
    """Compute retention score based on salience, temporal decay, and reinforcement."""
    salience_map = {'architecture': 0.9, 'decision': 0.9, 'preference': 0.85, 'pattern': 0.8, 'bug': 0.7, 'todo': 0.6}
    salience = salience_map.get(entry.get('category', 'general'), 0.5)
    days = (now - entry.get('timestamp', now)) / 86400
    decay = math.exp(-0.01 * days)
    access_history = entry.get('access_history', [])
    if access_history:
        reinforcement = min(sum(1.0 / max(1, (now - ts) / 86400) for ts in access_history[-20:]) * 0.05, 0.3)
    else:
        access_count = entry.get('access_count', 0)
        reinforcement = min(access_count * 0.05, 0.3)
    return salience * decay + reinforcement


def _get_tier(entry: dict[str, Any], now: float) -> str:
    """Determine tier using retention scoring. PINNED_CATEGORIES always hot."""
    category = entry.get("category", "general")
    if category in PINNED_CATEGORIES:
        return "hot"
    retention = _compute_retention(entry, now)
    if retention >= 0.5:
        return "hot"
    if retention >= 0.25:
        return "warm"
    return "cold"


def compress_memory(repo_root: Path) -> str:
    """Compress memory via category-aware merging with pattern extraction."""
    storage = get_storage(repo_root)
    entries = _as_list(storage.read_collection(Collections.MEMORY))

    if len(entries) <= COMPRESS_THRESHOLD:
        return f"Memory has {len(entries)} entries (threshold: {COMPRESS_THRESHOLD}). No compression needed."

    now = time.time()
    hot = []
    cold_by_category: dict[str, list[dict[str, Any]]] = {}

    for entry in entries:
        tier = _get_tier(entry, now)
        if tier == "hot":
            hot.append(entry)
        else:
            cat = entry.get("category", "general")
            cold_by_category.setdefault(cat, []).append(entry)

    compressed = list(hot)
    merged_count = 0
    patterns_extracted = 0

    for cat, items in cold_by_category.items():
        if len(items) <= 3:
            compressed.extend(items)
            continue

        # Jaccard consolidation
        consolidated_ids: set[int] = set()
        for i in range(len(items)):
            if items[i].get("id") in consolidated_ids:
                continue
            for j in range(i + 1, len(items)):
                if items[j].get("id") in consolidated_ids:
                    continue
                tokens_a = set(items[i].get("content", "").lower().split())
                tokens_b = set(items[j].get("content", "").lower().split())
                if not tokens_a or not tokens_b:
                    continue
                jaccard = len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
                if jaccard > 0.5:
                    _next_id(entries + compressed)
                    merged_content = items[i].get("content", "") + " | " + items[j].get("content", "")
                    if len(merged_content) > 500:
                        merged_content = merged_content[:497] + "..."
                    items[i]["content"] = merged_content
                    items[i]["access_count"] = max(items[i].get("access_count", 0), items[j].get("access_count", 0))
                    items[j]["consolidated_into"] = items[i].get("id")
                    consolidated_ids.add(items[j].get("id"))
                    merged_count += 1

        remaining = [it for it in items if it.get("id") not in consolidated_ids]
        clusters = _cluster_by_similarity(remaining, threshold=0.5)

        for cluster in clusters:
            if len(cluster) == 1:
                compressed.append(cluster[0])
                continue
            merged = _merge_cluster(cluster, cat, now)
            compressed.append(merged)
            merged_count += len(cluster) - 1
            if len(cluster) >= 3:
                pattern = _extract_pattern(cluster, cat)
                if pattern:
                    compressed.append(pattern)
                    patterns_extracted += 1

    storage.write_collection(Collections.MEMORY, compressed)
    _refresh_rule(repo_root)
    parts = [f"Compressed memory: {len(entries)} → {len(compressed)} entries ({merged_count} merged)"]
    if patterns_extracted:
        parts.append(f", {patterns_extracted} patterns extracted")
    return "".join(parts) + "."


def _cluster_by_similarity(
    items: list[dict[str, Any]], threshold: float = 0.5
) -> list[list[dict[str, Any]]]:
    """Cluster memories by pairwise SparseEmbedding similarity (greedy)."""
    from ..embeddings import KeywordEmbeddingProvider

    provider = KeywordEmbeddingProvider()
    embeddings = [provider.embed(item.get("content", "")) for item in items]
    assigned = [False] * len(items)
    clusters: list[list[dict[str, Any]]] = []

    for i in range(len(items)):
        if assigned[i]:
            continue
        cluster = [items[i]]
        assigned[i] = True
        for j in range(i + 1, len(items)):
            if assigned[j]:
                continue
            if embeddings[i].score(embeddings[j]) >= threshold:
                cluster.append(items[j])
                assigned[j] = True
        clusters.append(cluster)

    return clusters


def _merge_cluster(
    cluster: list[dict[str, Any]], category: str, now: float
) -> dict[str, Any]:
    """Merge a cluster of similar memories into one consolidated entry."""
    latest_ts = max(e.get("timestamp", now) for e in cluster)
    max_confidence = max(e.get("confidence", 0.8) for e in cluster)
    total_recalls = sum(e.get("recall_count", 0) for e in cluster)
    contents = [e.get("content", "") for e in cluster]
    merged_content = _deduplicate_content(contents)

    return {
        "id": cluster[0]["id"],
        "timestamp": latest_ts,
        "category": category,
        "content": merged_content,
        "confidence": max_confidence,
        "source": "consolidation",
        "recall_count": total_recalls,
        "last_recalled": max((e.get("last_recalled") for e in cluster if e.get("last_recalled")), default=None),
        "tier": cluster[0].get("tier", "session"),
        "merged_from": len(cluster),
    }


def _deduplicate_content(contents: list[str]) -> str:
    """Merge multiple content strings, removing redundant sentences."""
    seen_sentences: set[str] = set()
    unique_parts: list[str] = []

    for content in contents:
        sentences = re.split(r'[.;]\s+', content.strip())
        for sentence in sentences:
            normalized = sentence.strip().lower()
            if len(normalized) < 5:
                continue
            if normalized not in seen_sentences:
                seen_sentences.add(normalized)
                unique_parts.append(sentence.strip())

    merged = ". ".join(unique_parts)
    if len(merged) > 500:
        merged = merged[:497] + "..."
    return merged


def _extract_pattern(cluster: list[dict[str, Any]], category: str) -> dict[str, Any] | None:
    """Extract a recurring pattern from a cluster of related memories."""
    from ..embeddings import KeywordEmbeddingProvider

    contents = [e.get("content", "") for e in cluster]
    provider = KeywordEmbeddingProvider()
    token_counts: dict[str, int] = {}
    for content in contents:
        emb = provider.embed(content)
        for token in emb.counts:
            token_counts[token] = token_counts.get(token, 0) + 1

    threshold = len(cluster) * 0.6
    common_tokens = [t for t, c in token_counts.items() if c >= threshold and len(t) > 2]

    if len(common_tokens) < 2:
        return None

    pattern_desc = f"[pattern from {len(cluster)} entries] Common theme in {category}: {', '.join(common_tokens[:10])}"

    return {
        "id": cluster[0]["id"] + 900000,
        "timestamp": time.time(),
        "category": "pattern",
        "content": pattern_desc,
        "confidence": 0.7,
        "source": "pattern_extraction",
        "recall_count": 0,
        "last_recalled": None,
        "tier": "persistent",
        "extracted_from_count": len(cluster),
    }


# Contradiction signals
_NEGATION_PAIRS = [
    ("use", "don't use"), ("use", "avoid"), ("use", "never use"),
    ("always", "never"), ("enable", "disable"), ("add", "remove"),
    ("should", "should not"), ("must", "must not"),
]


def detect_contradictions(repo_root: Path) -> list[dict[str, Any]]:
    """Find memories/decisions that contradict each other."""
    from ..embeddings import KeywordEmbeddingProvider

    storage = get_storage(repo_root)
    memories = _as_list(storage.read_collection(Collections.MEMORY))
    decisions = _as_list(storage.read_collection(Collections.DECISIONS))

    statements = []
    for m in memories:
        statements.append({"type": "memory", "id": m.get("id"), "text": m.get("content", "")})
    for d in decisions:
        statements.append({"type": "decision", "id": d.get("id"), "text": d.get("decision", "")})

    contradictions = []
    provider = KeywordEmbeddingProvider()

    for i, a in enumerate(statements):
        for b in statements[i + 1:]:
            sim = provider.embed(a["text"]).score(provider.embed(b["text"]))
            if sim < 0.3:
                continue
            a_lower = a["text"].lower()
            b_lower = b["text"].lower()
            for pos, neg in _NEGATION_PAIRS:
                if (pos in a_lower and neg in b_lower) or (neg in a_lower and pos in b_lower):
                    contradictions.append({
                        "a": {"type": a["type"], "id": a["id"], "text": a["text"][:100]},
                        "b": {"type": b["type"], "id": b["id"], "text": b["text"][:100]},
                        "similarity": round(sim, 2),
                    })
                    break

    return contradictions


def bulk_forget(repo_root: Path, before: float | None = None, category: str | None = None, branch: str | None = None) -> str:
    """Delete memories matching criteria. Records in audit trail."""
    storage = get_storage(repo_root)
    entries = _as_list(storage.read_collection(Collections.MEMORY))
    original_count = len(entries)

    remaining = []
    for e in entries:
        matches = True
        if before is not None and e.get("timestamp", 0) >= before:
            matches = False
        if category is not None and e.get("category") != category:
            matches = False
        if branch is not None and e.get("branch") != branch:
            matches = False
        if matches and (before is not None or category is not None or branch is not None):
            continue
        remaining.append(e)

    deleted = original_count - len(remaining)
    storage.write_collection(Collections.MEMORY, remaining)

    record_audit(repo_root, 'bulk_forget', str(deleted), 'memory',
                 f"before={before} category={category} branch={branch}")
    _refresh_rule(repo_root)
    return f"Deleted {deleted} memories (before={before}, category={category}, branch={branch})."


def auto_forget_sweep(repo_root: Path) -> str:
    """Auto-forget sweep: TTL expiry, contradiction pruning, low-value pruning."""
    storage = get_storage(repo_root)
    entries = _as_list(storage.read_collection(Collections.MEMORY))
    now = time.time()
    actions: list[str] = []

    # TTL expiry
    ttl_expired = []
    for e in entries:
        if e.get("forget_after") and e["forget_after"] < now and not e.get("evicted"):
            e["evicted"] = True
            ttl_expired.append(e.get("id"))
    if ttl_expired:
        actions.append(f"TTL expired: {len(ttl_expired)}")

    # Contradiction pruning
    active = [e for e in entries if not e.get("evicted") and not e.get("superseded_by")]
    by_cat: dict[str, list[dict]] = {}
    for e in active:
        by_cat.setdefault(e.get("category", "general"), []).append(e)
    superseded_count = 0
    for cat, items in by_cat.items():
        for i in range(len(items)):
            if items[i].get("superseded_by"):
                continue
            for j in range(i + 1, len(items)):
                if items[j].get("superseded_by"):
                    continue
                sim = _text_similarity(items[i].get("content", ""), items[j].get("content", ""))
                if sim > 0.9:
                    items[i]["superseded_by"] = items[j].get("id")
                    superseded_count += 1
                    break
    if superseded_count:
        actions.append(f"Superseded: {superseded_count}")

    # Low-value pruning — evict based on retention score
    low_value = 0
    EVICTION_THRESHOLD = 0.15  # Memories scoring below this get evicted
    MAX_ACTIVE = 200  # Hard cap on active memories

    active_after_supersede = [e for e in entries if not e.get("evicted") and not e.get("superseded_by")]

    # Only evict if we're over the cap
    if len(active_after_supersede) > MAX_ACTIVE:
        scored = []
        for e in active_after_supersede:
            if e.get("category") in PINNED_CATEGORIES:
                continue  # Never evict decisions/architecture/preferences
            score = _compute_retention(e, now)
            scored.append((score, e))

        scored.sort(key=lambda x: x[0])

        # Evict lowest-scoring memories until we're under the cap
        to_evict = len(active_after_supersede) - MAX_ACTIVE
        for score, e in scored[:to_evict]:
            if score < EVICTION_THRESHOLD:
                e["evicted"] = True
                e["evicted_at"] = now
                e["eviction_reason"] = f"retention_score={score:.3f}"
                low_value += 1

    # Also evict very old zero-access memories regardless of cap
    for e in entries:
        if e.get("evicted") or e.get("category") in PINNED_CATEGORIES:
            continue
        age_days = (now - e.get("timestamp", now)) / 86400
        if age_days > 90 and e.get("access_count", 0) == 0 and e.get("importance", 2) <= 2:
            e["evicted"] = True
            e["evicted_at"] = now
            e["eviction_reason"] = "stale_90d_zero_access"
            low_value += 1

    if low_value:
        actions.append(f"Low-retention evicted: {low_value}")

    storage.write_collection(Collections.MEMORY, entries)

    if actions:
        record_audit(repo_root, "auto_forget_sweep", "", "memory", "; ".join(actions))

    return "; ".join(actions) if actions else "No cleanup needed."
