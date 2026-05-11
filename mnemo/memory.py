"""Persistent memory store with tiered retrieval and auto-categorization."""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any

from .config import CONTEXT_FILE, DECISIONS_FILE, MEMORY_FILE, mnemo_path
from .retrieval import semantic_query, index_chunks
from .storage import Collections, get_storage
from .chunking import Chunk

MAX_OUTPUT_CHARS = 75000  # Hard limit for MCP response
RECALL_BUDGET = 12000  # Target: keep recall small (~3K tokens)
MEMORY_TOKEN_BUDGET = 1000  # ~1000 tokens for memory section
TOKEN_CHAR_RATIO = 4  # 1 token ≈ 4 chars

# Tiering thresholds (seconds)
HOT_THRESHOLD = 7 * 24 * 3600  # 7 days
WARM_THRESHOLD = 30 * 24 * 3600  # 30 days

# Categories that are always hot (never demoted)
PINNED_CATEGORIES = {"architecture", "preference", "decision"}

# Auto-categorization patterns
_CATEGORY_PATTERNS = {
    "bug": re.compile(
        r"\b(fix|bug|error|crash|null|exception|broken|issue|regression|failed)\b", re.I
    ),
    "architecture": re.compile(
        r"\b(chose|decided|architecture|design|pattern|structure|migrate|refactor)\b", re.I
    ),
    "preference": re.compile(
        r"\b(always|never|convention|naming|prefer|style|standard|rule)\b", re.I
    ),
    "todo": re.compile(
        r"\b(todo|later|follow.?up|need to|should|plan|future|next)\b", re.I
    ),
    "pattern": re.compile(
        r"\b(pattern|similar|handler|implements|base class|interface|abstract)\b", re.I
    ),
}

MEMORY_NAMESPACE = "memory"
COMPRESS_THRESHOLD = 50  # Trigger compression when memory exceeds this count
DEDUP_SIMILARITY_THRESHOLD = 0.85  # Skip storing if this similar to recent entry
_REFRESH_COOLDOWN = 5.0  # Seconds between context file refreshes
_last_refresh_time: float = 0


def compress_memory(repo_root: Path) -> str:
    """Compress memory by grouping similar entries by category and merging."""
    storage = get_storage(repo_root)
    entries = _as_list(storage.read_collection(Collections.MEMORY))

    if len(entries) <= COMPRESS_THRESHOLD:
        return f"Memory has {len(entries)} entries (threshold: {COMPRESS_THRESHOLD}). No compression needed."

    now = time.time()
    # Keep hot entries as-is, compress cold ones
    hot = []
    cold_by_category: dict[str, list[dict[str, Any]]] = {}

    for entry in entries:
        tier = _get_tier(entry, now)
        if tier == "hot":
            hot.append(entry)
        else:
            cat = entry.get("category", "general")
            cold_by_category.setdefault(cat, []).append(entry)

    # Merge cold entries per category into summaries
    compressed = list(hot)
    merged_count = 0
    for cat, items in cold_by_category.items():
        if len(items) <= 3:
            compressed.extend(items)
            continue
        # Group into batches of 5 and merge
        for i in range(0, len(items), 5):
            batch = items[i:i + 5]
            if len(batch) == 1:
                compressed.append(batch[0])
                continue
            merged_content = "; ".join(e.get("content", "")[:100] for e in batch)
            compressed.append({
                "id": batch[0]["id"],
                "timestamp": batch[-1].get("timestamp", now),
                "category": cat,
                "content": f"[merged {len(batch)}] {merged_content}",
            })
            merged_count += len(batch) - 1

    storage.write_collection(Collections.MEMORY, compressed)
    _refresh_rule(repo_root)
    return f"Compressed memory: {len(entries)} → {len(compressed)} entries ({merged_count} merged)."


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


def _get_tier(entry: dict[str, Any], now: float) -> str:
    """Determine tier for a memory entry."""
    category = entry.get("category", "general")
    if category in PINNED_CATEGORIES:
        return "hot"
    age = now - entry.get("timestamp", now)
    if age <= HOT_THRESHOLD:
        return "hot"
    if age <= WARM_THRESHOLD:
        return "warm"
    return "cold"


def _infer_search_category(query: str) -> str | None:
    """Infer which category to search based on query text."""
    scores: dict[str, int] = {}
    for category, pattern in _CATEGORY_PATTERNS.items():
        matches = pattern.findall(query)
        if matches:
            scores[category] = len(matches)
    if not scores:
        return None
    return max(scores, key=scores.get)


def _memory_to_chunk(entry: dict[str, Any]) -> Chunk:
    """Convert a memory entry to a Chunk for vector indexing."""
    content = entry.get("content", "")
    return Chunk(
        id=f"memory-{entry.get('id', 0)}",
        chunk_type="memory",
        path="memory",
        language="text",
        symbol=entry.get("category", "general"),
        content=content,
        metadata={"category": entry.get("category", "general")},
    )


def _index_memory_entry(repo_root: Path, entry: dict[str, Any]) -> None:
    """Index a single memory entry into the vector store."""
    try:
        index_chunks(repo_root, MEMORY_NAMESPACE, [_memory_to_chunk(entry)])
    except Exception as exc:
        print(f"[mnemo] Failed to index memory entry: {exc}", file=sys.stderr)


def _graph_link_entry(repo_root: Path, node_id: str, node_type: str, text: str) -> None:
    """Auto-link a new memory/decision node to the knowledge graph."""
    try:
        from .graph.local import LocalGraph
        from .graph import Node, Edge
        graph = LocalGraph(repo_root)
        if not graph.exists():
            return
        graph.upsert_node(Node(id=node_id, type=node_type, name=text[:80], properties={"full_text": text}))
        # Find referenced entities
        for nid, data in graph.graph.nodes(data=True):
            if data.get("type") in ("class", "service", "interface") and len(data.get("name", "")) >= 4:
                if data["name"] in text:
                    graph.upsert_edge(Edge(source=node_id, target=nid, type="references"))
        graph.save()
    except Exception:
        pass  # Non-fatal


def _refresh_rule(repo_root: Path) -> None:
    """Update installed client context files with latest context (debounced)."""
    global _last_refresh_time
    now = time.time()
    if now - _last_refresh_time < _REFRESH_COOLDOWN:
        return
    _last_refresh_time = now
    from .init import refresh_context_files
    refresh_context_files(repo_root)


def _as_list(data: Any) -> list[dict[str, Any]]:
    return data if isinstance(data, list) else []


def _as_dict(data: Any) -> dict[str, Any]:
    return data if isinstance(data, dict) else {}


def _index_changed_files(repo_root: Path, old_hashes: dict[str, Any]) -> None:
    """Incrementally index only files that changed since last hash snapshot."""
    from .repo_map import _extract_file, _should_ignore, MAX_FILE_SIZE
    from .config import SUPPORTED_EXTENSIONS
    from .chunking import make_code_chunks
    import hashlib

    chunks = []
    for ext, language in SUPPORTED_EXTENSIONS.items():
        for filepath in repo_root.rglob(f"*{ext}"):
            if _should_ignore(filepath) or filepath.stat().st_size > MAX_FILE_SIZE:
                continue
            rel = str(filepath.relative_to(repo_root))
            try:
                content = filepath.read_bytes()
                current_hash = hashlib.md5(content).hexdigest()
            except (OSError, PermissionError):
                continue
            if old_hashes.get(rel) == current_hash:
                continue
            # This file changed — parse and index it
            info = _extract_file(content, language)
            if info:
                chunks.extend(make_code_chunks(rel, language, info))

    if chunks:
        try:
            index_chunks(repo_root, "code", chunks)
        except Exception as exc:
            print(f"[mnemo] Failed to index changed files: {exc}", file=sys.stderr)


def _text_similarity(a: str, b: str) -> float:
    """Quick token overlap similarity between two strings."""
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    overlap = len(tokens_a & tokens_b)
    return overlap / max(len(tokens_a), len(tokens_b))


def _next_id(entries: list[dict[str, Any]]) -> int:
    """Generate the next unique ID from existing entries."""
    if not entries:
        return 1
    return max(e.get("id", 0) for e in entries) + 1


def add_memory(repo_root: Path, content: str, category: str = "general") -> dict[str, Any]:
    """Add a memory entry with deduplication, auto-categorization, and vector indexing."""
    storage = get_storage(repo_root)
    entries = _as_list(storage.read_collection(Collections.MEMORY))

    # Auto-categorize if user didn't specify
    if category == "general":
        category = _auto_categorize(content)

    # Deduplication: check recent entries for high similarity
    for existing in entries[-20:]:
        if _text_similarity(content, existing.get("content", "")) >= DEDUP_SIMILARITY_THRESHOLD:
            # Update timestamp instead of duplicating
            existing["timestamp"] = time.time()
            storage.write_collection(Collections.MEMORY, entries)
            return existing

    entry = {
        "id": _next_id(entries),
        "timestamp": time.time(),
        "category": category,
        "content": content,
    }
    entries.append(entry)
    storage.write_collection(Collections.MEMORY, entries)

    # Index into vector store for semantic search
    _index_memory_entry(repo_root, entry)

    # Auto-link to knowledge graph
    _graph_link_entry(repo_root, f"memory:{entry['id']}", "memory", content)

    _refresh_rule(repo_root)
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
    """Record a decision with deduplication and refresh installed context files."""
    storage = get_storage(repo_root)
    entries = _as_list(storage.read_collection(Collections.DECISIONS))

    # Deduplication: skip if highly similar decision already exists
    for existing in entries:
        if _text_similarity(decision, existing.get("decision", "")) >= DEDUP_SIMILARITY_THRESHOLD:
            existing["timestamp"] = time.time()
            if reasoning and not existing.get("reasoning"):
                existing["reasoning"] = reasoning
            storage.write_collection(Collections.DECISIONS, entries)
            return existing

    entry = {
        "id": _next_id(entries),
        "timestamp": time.time(),
        "decision": decision,
        "reasoning": reasoning,
    }
    entries.append(entry)
    storage.write_collection(Collections.DECISIONS, entries)

    # Auto-link to knowledge graph
    _graph_link_entry(repo_root, f"decision:{entry['id']}", "decision", decision)

    _refresh_rule(repo_root)
    return entry


def save_context(repo_root: Path, context: dict[str, Any]) -> None:
    """Save project context and refresh installed context files."""
    storage = get_storage(repo_root)
    existing = _as_dict(storage.read_collection(Collections.CONTEXT))
    existing.update(context)
    existing["last_updated"] = time.time()
    storage.write_collection(Collections.CONTEXT, existing)
    _refresh_rule(repo_root)


def search_memory(repo_root: Path, query: str, deep: bool = False) -> str:
    """Search memories semantically, auto-detecting category from query."""
    category = _infer_search_category(query)
    limit = 15 if deep else 7

    # Try semantic search with category filter first
    filters = {"category": category} if category else None
    results = semantic_query(repo_root, MEMORY_NAMESPACE, query, limit=limit, filters=filters)

    # If category filter returned few results, also search without filter
    if len(results) < 3:
        unfiltered = semantic_query(repo_root, MEMORY_NAMESPACE, query, limit=limit)
        seen_ids = {r.get("id") for r in results}
        for r in unfiltered:
            if r.get("id") not in seen_ids:
                results.append(r)
        results = results[:limit]

    # Fallback: keyword search in memory.json
    if not results:
        storage = get_storage(repo_root)
        entries = _as_list(storage.read_collection(Collections.MEMORY))
        query_lower = query.lower()
        matched = [e for e in entries if query_lower in e.get("content", "").lower()]
        results = [
            {"content": e["content"], "metadata": {"category": e.get("category", "general")}}
            for e in matched[-limit:]
        ]

    if not results:
        return f"No memories found for '{query}'."

    lines = [f"# Memory Search: '{query}'\n"]
    for r in results:
        content = r.get("content", "")
        # Strip the "memory general\n" prefix from vector store format
        if content.startswith("memory "):
            content = content.split("\n", 1)[-1] if "\n" in content else content
        meta = r.get("metadata", {})
        cat = meta.get("category", "general")
        lines.append(f"- [{cat}] {content}")

    # Hint if there might be more
    storage = get_storage(repo_root)
    total = len(_as_list(storage.read_collection(Collections.MEMORY)))
    if total > len(results) and not deep:
        lines.append(f"\n*Showing {len(results)} of {total} total memories. Search again with deep=true for more.*")
    return "\n".join(lines)


def lookup(repo_root: Path, query: str) -> str:
    """Look up detailed info for a specific file or folder - parses on demand."""
    from .repo_map import MAX_FILE_SIZE, SUPPORTED_EXTENSIONS, _extract_file, _should_ignore
    from .chunking import make_code_chunks
    from .retrieval import index_chunks

    query_lower = query.lower().strip("/")
    matches: list[tuple[str, dict[str, Any]]] = []
    discovered_chunks = []

    for ext, language in SUPPORTED_EXTENSIONS.items():
        for filepath in repo_root.rglob(f"*{ext}"):
            if _should_ignore(filepath) or filepath.stat().st_size > MAX_FILE_SIZE:
                continue
            rel = str(filepath.relative_to(repo_root))
            if query_lower not in rel.lower():
                continue
            try:
                source = filepath.read_bytes()
            except (OSError, PermissionError):
                continue
            info = _extract_file(source, language)
            if info:
                matches.append((rel, info))
                discovered_chunks.extend(make_code_chunks(rel, language, info))

    # Feed discovered code into the index for future queries
    if discovered_chunks:
        try:
            index_chunks(repo_root, "code", discovered_chunks)
        except Exception as exc:
            print(f"[mnemo] Failed to index discovered chunks: {exc}", file=sys.stderr)

    if not matches:
        return f"No files matching '{query}' found."

    lines = [f"# Details for '{query}'\n"]
    for filepath, info in sorted(matches):
        lines.append(f"## {filepath}")
        if info.get("imports"):
            lines.append("**Imports:** " + ", ".join(info["imports"]))
        for cls in info.get("classes", []):
            impl = f" : {cls['implements']}" if cls.get("implements") else ""
            lines.append(f"### `{cls['name']}{impl}`")
            for method in cls.get("methods", []):
                lines.append(f"- {method}")
        for function in info.get("functions", []):
            lines.append(f"- {function}")
        lines.append("")

    result = "\n".join(lines)
    if len(result) > MAX_OUTPUT_CHARS:
        result = result[:MAX_OUTPUT_CHARS]
        last_nl = result.rfind("\n")
        if last_nl > 0:
            result = result[:last_nl]
        result += "\n... (narrow your query for more details)"
    return result


def _recall_context(storage) -> str:
    """Recall project context section."""
    context = dict(_as_dict(storage.read_collection(Collections.CONTEXT)))
    context.pop("last_updated", None)
    if not context:
        return ""
    lines = ["# Project Context"]
    for key, value in context.items():
        lines.append(f"- **{key}**: {value}")
    lines.append("")
    return "\n".join(lines)


def _recall_decisions(storage) -> str:
    """Recall decisions section."""
    decisions = _as_list(storage.read_collection(Collections.DECISIONS))
    if not decisions:
        return ""
    lines = ["# Decisions"]
    for decision in decisions:
        reasoning = f" - {decision['reasoning']}" if decision.get("reasoning") else ""
        lines.append(f"- {decision['decision']}{reasoning}")
    lines.append("")
    return "\n".join(lines)


def _recall_memory(repo_root: Path, storage) -> str:
    """Recall tiered memory section with auto-compression."""
    memory = _as_list(storage.read_collection(Collections.MEMORY))

    if len(memory) > COMPRESS_THRESHOLD:
        compress_memory(repo_root)
        memory = _as_list(storage.read_collection(Collections.MEMORY))

    now = time.time()
    hot_memories = []
    category_counts: dict[str, int] = {}
    for entry in memory:
        tier = _get_tier(entry, now)
        cat = entry.get("category", "general")
        if tier == "hot":
            hot_memories.append(entry)
        else:
            category_counts[cat] = category_counts.get(cat, 0) + 1

    lines = []
    if hot_memories:
        lines.append("# Memory")
        char_budget = MEMORY_TOKEN_BUDGET * TOKEN_CHAR_RATIO
        for item in hot_memories:
            cat = f" [{item['category']}]" if item.get("category") != "general" else ""
            line = f"- {item['content']}{cat}"
            if char_budget - len(line) < 0:
                break
            char_budget -= len(line)
            lines.append(line)

    total_archived = sum(category_counts.values())
    if total_archived > 0:
        counts_str = ", ".join(f"{count} {cat}" for cat, count in sorted(category_counts.items()))
        lines.append(
            f"\n*{total_archived} more memories available ({counts_str})"
            f" — use mnemo_search_memory to find specific context.*"
        )
    lines.append("")
    return "\n".join(lines)


def _recall_active_task(repo_root: Path, storage) -> str:
    """Recall active task context section."""
    tasks = _as_list(storage.read_collection(Collections.TASKS))
    active_tasks = [task for task in tasks if task.get("status") == "active"]
    if not active_tasks:
        return ""
    lines = ["# Active Task Context"]
    active = active_tasks[-1]
    lines.append(f"- **{active.get('task_id', '')}**: {active.get('description', '')}")
    task_query = " ".join(filter(None, [
        str(active.get("task_id", "")),
        str(active.get("description", "")),
        " ".join(active.get("files", [])),
        str(active.get("notes", "")),
    ]))
    hits = semantic_query(repo_root, "code", task_query, limit=5)
    for hit in hits:
        meta = hit.get("metadata", {})
        lines.append(f"- Relevant: `{meta.get('path', '')}` :: `{meta.get('symbol', '')}`")
    lines.append("")
    return "\n".join(lines)


def _recall_recent_changes(base: Path) -> str:
    """Recall recent changes section."""
    from .repo_map import CHANGELOG_FILE
    changelog_path = base / CHANGELOG_FILE
    if not changelog_path.exists():
        return ""
    try:
        changelog = json.loads(changelog_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ""
    if not changelog:
        return ""
    lines = ["# Recent Changes"]
    for entry in changelog[-5:]:
        if entry.get("added"):
            lines.append(f"- Added: {', '.join(entry['added'])}")
        if entry.get("modified"):
            lines.append(f"- Modified: {', '.join(entry['modified'])}")
        if entry.get("deleted"):
            lines.append(f"- Deleted: {', '.join(entry['deleted'])}")
        if entry.get("renamed"):
            for new, old in entry["renamed"].items():
                lines.append(f"- Renamed: {old} -> {new}")
    lines.append("")
    return "\n".join(lines)


def _recall_repo_map(base: Path, header_size: int) -> str:
    """Recall repo map section using compact tree + graph summary."""
    # Graph summary (if available)
    graph_summary = ""
    graph_path = base / "graph.json"
    if graph_path.exists():
        try:
            from .graph.local import LocalGraph
            graph = LocalGraph(base.parent)
            s = graph.stats()
            node_types = s.get("node_types", {})
            top_types = sorted(node_types.items(), key=lambda x: x[1], reverse=True)[:5]
            graph_summary = f"Knowledge Graph: {s['nodes']} nodes, {s['edges']} edges ({', '.join(f'{c} {t}' for t, c in top_types)})\n"
            # Find hubs
            g = graph.graph
            degrees = [(nid, g.in_degree(nid) + g.out_degree(nid)) for nid in g.nodes]
            degrees.sort(key=lambda x: x[1], reverse=True)
            hubs = []
            for nid, deg in degrees[:5]:
                node = graph.get_node(nid)
                if node:
                    hubs.append(f"{node.name} ({node.type}, {deg} connections)")
            if hubs:
                graph_summary += f"Key hubs: {', '.join(hubs)}\n"
        except Exception:
            pass

    tree_path = base / "tree.md"
    if not tree_path.exists():
        summary_path = base / "summary.md"
        if not summary_path.exists():
            return ""
        content = summary_path.read_text(encoding="utf-8")
    else:
        content = tree_path.read_text(encoding="utf-8")

    lines = ["# Repo Map", "(use mnemo_lookup for method-level details, mnemo_graph for relationships)\n"]
    if graph_summary:
        lines.append(graph_summary)
    lines.append(content)
    return "\n".join(lines)


def recall(repo_root: Path) -> str:
    """Recall project memory with token-budgeted tiered retrieval."""
    from .repo_map import has_changes, save_repo_map

    base = mnemo_path(repo_root)
    if not base.exists():
        return ""

    if has_changes(repo_root):
        old_hashes = _as_dict(get_storage(repo_root).read_collection(Collections.HASHES))
        save_repo_map(repo_root, index=False)
        _index_changed_files(repo_root, old_hashes)

    storage = get_storage(repo_root)
    sections = [
        _recall_context(storage),
        _recall_decisions(storage),
        _recall_memory(repo_root, storage),
        _recall_active_task(repo_root, storage),
        _recall_recent_changes(base),
    ]
    # Repo map gets remaining budget
    header = "\n".join(s for s in sections if s)
    sections.append(_recall_repo_map(base, len(header)))

    return "\n".join(s for s in sections if s)
