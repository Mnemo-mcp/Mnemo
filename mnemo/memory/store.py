"""Memory CRUD operations: add, forget, decide, save context."""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from typing import Any

from ..storage import Collections, get_storage
from ..utils.privacy import strip_secrets
from ..utils.audit import record_audit

from ._shared import (
    logger,
    DEDUP_SIMILARITY_THRESHOLD,
    CONTRADICTION_SIMILARITY_THRESHOLD,
    _CATEGORY_PATTERNS,
    _TAG_PATTERNS,
    _IMPORTANCE_MAP,
    _FILE_PATH_RE,
    _STOP_WORDS,
    _as_list,
    _as_dict,
    _next_id,
    _text_similarity,
    _index_memory_entry,
    _graph_link_entry,
    _refresh_rule,
)
# _get_current_branch is accessed via `import mnemo.memory` at call time for mockability


def _auto_categorize(text: str) -> str:
    """Infer category from memory text content."""
    scores: dict[str, int] = {}
    for category, pattern in _CATEGORY_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            scores[category] = len(matches)
    if not scores:
        return "general"
    return max(scores, key=scores.get)


def _infer_confidence(content: str, source: str) -> float:
    """Infer confidence score based on source and content signals."""
    if source == "user":
        return 1.0
    if source in ("incident", "review"):
        return 0.9
    if any(w in content.lower() for w in ("maybe", "might", "possibly", "not sure", "i think")):
        return 0.5
    return 0.8


def _extract_concepts(content: str) -> list[str]:
    """Extract top 5 TF-IDF-like terms from content."""
    words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b', content.lower())
    words = [w for w in words if w not in _STOP_WORDS]
    tf: dict[str, int] = {}
    for w in words:
        tf[w] = tf.get(w, 0) + 1
    scored = [(count * (1 + len(word) * 0.1), word) for word, count in tf.items()]
    scored.sort(reverse=True)
    return [word for _, word in scored[:5]]


def _resolve_entities(repo_root: Path, content: str) -> str:
    """Resolve ambiguous references like 'this file' using active task context."""
    try:
        storage = get_storage(repo_root)
        tasks = _as_list(storage.read_collection(Collections.TASKS))
        active = [t for t in tasks if t.get("status") == "active"]
        if not active:
            return content
        task = active[-1]
        files = task.get("files", [])
        desc = task.get("description", "")
        if files:
            content = re.sub(r'\b(this file|the file)\b', files[0], content, flags=re.I)
        svc_match = re.search(r'\b([A-Z][a-zA-Z]{3,}(?:Service|Controller|Handler)?)\b', desc)
        if svc_match:
            content = re.sub(r'\b(this service|the service)\b', svc_match.group(1), content, flags=re.I)
    except Exception as exc:
        logger.debug(f"Entity resolution failed: {exc}")


def add_memory(repo_root: Path, content: str, category: str = "general", source: str = "user", tags: list[str] | None = None) -> dict[str, Any]:
    """Add a memory entry with deduplication, auto-categorization, tiering, tagging, and vector indexing."""
    from .hierarchy import assign_tier, expire_working_memory

    content, _ = strip_secrets(content)
    content = _resolve_entities(repo_root, content)

    storage = get_storage(repo_root)
    entries = _as_list(storage.read_collection(Collections.MEMORY))

    if category == "general":
        category = _auto_categorize(content)

    expire_working_memory(repo_root)

    # Deduplication
    for existing in entries[-20:]:
        if _text_similarity(content, existing.get("content", "")) >= DEDUP_SIMILARITY_THRESHOLD:
            existing["timestamp"] = time.time()
            existing["recall_count"] = existing.get("recall_count", 0)
            storage.write_collection(Collections.MEMORY, entries)
            return existing

    tier = assign_tier(category, content)

    # Auto-tagging
    auto_tags = list(tags) if tags else []
    for tag_name, pattern in _TAG_PATTERNS.items():
        if pattern.search(content) and tag_name not in auto_tags:
            auto_tags.append(tag_name)

    files = _FILE_PATH_RE.findall(content)
    concepts = _extract_concepts(content)
    importance = _IMPORTANCE_MAP.get(category, 2)

    entry = {
        "id": _next_id(entries),
        "timestamp": time.time(),
        "category": category,
        "content": content,
        "confidence": _infer_confidence(content, source),
        "source": source,
        "recall_count": 0,
        "last_recalled": None,
        "tier": tier,
        "branch": sys.modules[__name__.rsplit(".", 1)[0]]._get_current_branch(repo_root),
        "tags": auto_tags,
        "files": files[:10],
        "concepts": concepts,
        "importance": importance,
    }

    # Contradiction detection — supersede older memories with similar content in same category
    same_cat = [e for e in entries if e.get("category") == category and not e.get("superseded_by")][-30:]
    for existing in same_cat:
        sim = _text_similarity(content, existing.get("content", ""))
        if CONTRADICTION_SIMILARITY_THRESHOLD <= sim < DEDUP_SIMILARITY_THRESHOLD:
            existing["superseded_by"] = entry["id"]
            existing["superseded_at"] = time.time()

    entries.append(entry)
    storage.write_collection(Collections.MEMORY, entries)

    _index_memory_entry(repo_root, entry)
    _graph_link_entry(repo_root, f"memory:{entry['id']}", "memory", content)
    _refresh_rule(repo_root)
    record_audit(repo_root, 'add_memory', str(entry['id']), 'memory', content[:100])
    return entry


def forget_memory(repo_root: Path, memory_id: int) -> str:
    """Delete a specific memory entry by ID."""
    storage = get_storage(repo_root)
    entries = _as_list(storage.read_collection(Collections.MEMORY))
    before = len(entries)
    entries = [e for e in entries if e.get("id") != memory_id]
    if len(entries) == before:
        return f"Memory #{memory_id} not found."
    storage.write_collection(Collections.MEMORY, entries)
    _refresh_rule(repo_root)
    return f"Memory #{memory_id} deleted."


def add_decision(repo_root: Path, decision: str, reasoning: str = "") -> dict[str, Any]:
    """Record a decision with deduplication, contradiction detection, and refresh installed context files."""
    decision, _ = strip_secrets(decision)
    if reasoning:
        reasoning, _ = strip_secrets(reasoning)

    storage = get_storage(repo_root)
    entries = _as_list(storage.read_collection(Collections.DECISIONS))

    # Deduplication
    for existing in entries:
        if existing.get("active", True) and _text_similarity(decision, existing.get("decision", "")) >= DEDUP_SIMILARITY_THRESHOLD:
            existing["timestamp"] = time.time()
            if reasoning and not existing.get("reasoning"):
                existing["reasoning"] = reasoning
            storage.write_collection(Collections.DECISIONS, entries)
            return existing

    new_id = _next_id(entries)
    entry = {
        "id": new_id,
        "timestamp": time.time(),
        "decision": decision,
        "reasoning": reasoning,
        "active": True,
        "superseded_by": None,
    }

    # Detect contradictions
    superseded = []
    for existing in entries:
        if not existing.get("active", True):
            continue
        sim = _text_similarity(decision, existing.get("decision", ""))
        if CONTRADICTION_SIMILARITY_THRESHOLD <= sim < DEDUP_SIMILARITY_THRESHOLD:
            existing["active"] = False
            existing["superseded_by"] = new_id
            superseded.append(existing)

    entries.append(entry)
    storage.write_collection(Collections.DECISIONS, entries)

    # Cascade staleness
    if superseded:
        try:
            from ..graph.local import LocalGraph
            graph = LocalGraph(repo_root)
            if graph.exists():
                for old in superseded:
                    old_node_id = f"decision:{old['id']}"
                    for _, target, key, data in graph.graph.out_edges(old_node_id, keys=True, data=True):
                        graph.graph.edges[old_node_id, target, key]["stale"] = True
                graph.save()
        except Exception as exc:
            logger.debug(f"Graph stale-marking failed: {exc}")
    _refresh_rule(repo_root)
    record_audit(repo_root, 'add_decision', str(entry['id']), 'decision', decision[:100])

    if superseded:
        entry["_superseded"] = superseded
    return entry


def save_context(repo_root: Path, context: dict[str, Any]) -> None:
    """Save project context and refresh installed context files."""
    storage = get_storage(repo_root)
    existing = _as_dict(storage.read_collection(Collections.CONTEXT))
    existing.update(context)
    existing["last_updated"] = time.time()
    storage.write_collection(Collections.CONTEXT, existing)
    _refresh_rule(repo_root)
