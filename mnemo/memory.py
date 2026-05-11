"""Persistent memory store with tiered retrieval and auto-categorization."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from .config import CONTEXT_FILE, DECISIONS_FILE, MEMORY_FILE, mnemo_path
from .retrieval import semantic_query, index_chunks
from .storage import Collections, get_storage
from .chunking import Chunk

MAX_OUTPUT_CHARS = 75000  # Hard limit for MCP response
RECALL_BUDGET = 12000  # Target: keep recall small (~3K tokens)
MEMORY_TOKEN_BUDGET = 4000  # Max chars for memory section in recall

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
    return Chunk(
        id=f"memory-{entry.get('id', 0)}",
        path="memory",
        symbol=entry.get("category", "general"),
        content=entry.get("content", ""),
        language="text",
        chunk_type="memory",
        metadata={"category": entry.get("category", "general")},
    )


def _index_memory_entry(repo_root: Path, entry: dict[str, Any]) -> None:
    """Index a single memory entry into the vector store."""
    try:
        index_chunks(repo_root, MEMORY_NAMESPACE, [_memory_to_chunk(entry)])
    except Exception:
        pass


def _refresh_rule(repo_root: Path) -> None:
    """Update installed client context files with latest context."""
    from .init import refresh_context_files

    refresh_context_files(repo_root)


def _as_list(data: Any) -> list[dict[str, Any]]:
    return data if isinstance(data, list) else []


def _as_dict(data: Any) -> dict[str, Any]:
    return data if isinstance(data, dict) else {}


def add_memory(repo_root: Path, content: str, category: str = "general") -> dict[str, Any]:
    """Add a memory entry with auto-categorization and vector indexing."""
    storage = get_storage(repo_root)
    entries = _as_list(storage.read_collection(Collections.MEMORY))

    # Auto-categorize if user didn't specify
    if category == "general":
        category = _auto_categorize(content)

    entry = {
        "id": len(entries) + 1,
        "timestamp": time.time(),
        "category": category,
        "content": content,
    }
    entries.append(entry)
    storage.write_collection(Collections.MEMORY, entries)

    # Index into vector store for semantic search
    _index_memory_entry(repo_root, entry)

    _refresh_rule(repo_root)
    return entry


def add_decision(repo_root: Path, decision: str, reasoning: str = "") -> dict[str, Any]:
    """Record a decision and refresh installed context files."""
    storage = get_storage(repo_root)
    entries = _as_list(storage.read_collection(Collections.DECISIONS))
    entry = {
        "id": len(entries) + 1,
        "timestamp": time.time(),
        "decision": decision,
        "reasoning": reasoning,
    }
    entries.append(entry)
    storage.write_collection(Collections.DECISIONS, entries)
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
        except Exception:
            pass

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


def recall(repo_root: Path) -> str:
    """Recall project memory with token-budgeted tiered retrieval."""
    from .repo_map import CHANGELOG_FILE, has_changes, save_repo_map

    base = mnemo_path(repo_root)
    if not base.exists():
        return ""

    if has_changes(repo_root):
        save_repo_map(repo_root, index=False)

    storage = get_storage(repo_root)
    sections: list[str] = []

    # --- Always included: Project Context ---
    context = dict(_as_dict(storage.read_collection(Collections.CONTEXT)))
    context.pop("last_updated", None)
    if context:
        sections.append("# Project Context")
        for key, value in context.items():
            sections.append(f"- **{key}**: {value}")
        sections.append("")

    # --- Always included: Decisions ---
    decisions = _as_list(storage.read_collection(Collections.DECISIONS))
    if decisions:
        sections.append("# Decisions")
        for decision in decisions:
            reasoning = f" - {decision['reasoning']}" if decision.get("reasoning") else ""
            sections.append(f"- {decision['decision']}{reasoning}")
        sections.append("")

    # --- Tiered Memory: only hot tier in recall ---
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

    if hot_memories:
        sections.append("# Memory")
        char_budget = MEMORY_TOKEN_BUDGET
        for item in hot_memories:
            cat = f" [{item['category']}]" if item.get("category") != "general" else ""
            line = f"- {item['content']}{cat}"
            if char_budget - len(line) < 0:
                break
            char_budget -= len(line)
            sections.append(line)

    # Show summary of non-hot memories
    total_archived = sum(category_counts.values())
    if total_archived > 0:
        counts_str = ", ".join(f"{count} {cat}" for cat, count in sorted(category_counts.items()))
        sections.append(
            f"\n*{total_archived} more memories available ({counts_str})"
            f" — use mnemo_search_memory to find specific context.*"
        )
    sections.append("")

    # --- Always included: Active Task ---
    tasks = _as_list(storage.read_collection(Collections.TASKS))
    active_tasks = [task for task in tasks if task.get("status") == "active"]
    if active_tasks:
        sections.append("# Active Task Context")
        active = active_tasks[-1]
        sections.append(f"- **{active.get('task_id', '')}**: {active.get('description', '')}")
        task_query = " ".join(
            filter(
                None,
                [
                    str(active.get("task_id", "")),
                    str(active.get("description", "")),
                    " ".join(active.get("files", [])),
                    str(active.get("notes", "")),
                ],
            )
        )
        hits = semantic_query(repo_root, "code", task_query, limit=5)
        for hit in hits:
            meta = hit.get("metadata", {})
            sections.append(f"- Relevant: `{meta.get('path', '')}` :: `{meta.get('symbol', '')}`")
        sections.append("")

    # --- Recent Changes ---
    changelog_path = base / CHANGELOG_FILE
    if changelog_path.exists():
        changelog = json.loads(changelog_path.read_text(encoding="utf-8"))
        if changelog:
            sections.append("# Recent Changes")
            for entry in changelog[-5:]:
                if entry.get("added"):
                    sections.append(f"- Added: {', '.join(entry['added'])}")
                if entry.get("modified"):
                    sections.append(f"- Modified: {', '.join(entry['modified'])}")
                if entry.get("deleted"):
                    sections.append(f"- Deleted: {', '.join(entry['deleted'])}")
                if entry.get("renamed"):
                    for new, old in entry["renamed"].items():
                        sections.append(f"- Renamed: {old} -> {new}")
            sections.append("")

    # --- Repo Map (budgeted) ---
    summary_path = base / "summary.md"
    if summary_path.exists():
        summary = summary_path.read_text(encoding="utf-8")
        sections.append("# Repo Map")
        sections.append("(use mnemo_lookup for method-level details)\n")

        header_size = len("\n".join(sections))
        budget = RECALL_BUDGET - header_size
        if len(summary) > budget:
            summary = summary[:budget]
            last_nl = summary.rfind("\n")
            if last_nl > 0:
                summary = summary[:last_nl]
            summary += "\n... (use mnemo_lookup for details)"
        sections.append(summary)

    return "\n".join(sections)
