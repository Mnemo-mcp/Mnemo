"""Persistent memory store for decisions, context, and notes."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .config import CONTEXT_FILE, DECISIONS_FILE, MEMORY_FILE, mnemo_path
from .retrieval import semantic_query
from .storage import Collections, get_storage

MAX_OUTPUT_CHARS = 75000  # Hard limit for MCP response
RECALL_BUDGET = 12000  # Target: keep recall small (~3K tokens)
MAX_MEMORY_ENTRIES = 50  # Keep last 50 entries, summarize older ones


def _refresh_rule(repo_root: Path) -> None:
    """Update installed client context files with latest context."""
    from .init import refresh_context_files

    refresh_context_files(repo_root)


def _as_list(data: Any) -> list[dict[str, Any]]:
    return data if isinstance(data, list) else []


def _as_dict(data: Any) -> dict[str, Any]:
    return data if isinstance(data, dict) else {}


def _compact_memory(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """When memory exceeds limit, compress old entries into a summary."""
    if len(entries) <= MAX_MEMORY_ENTRIES:
        return entries

    keep = entries[-30:]
    old = entries[:-30]
    summary_lines = [entry["content"] for entry in old[-20:] if entry.get("content")]
    summary = "Previous context: " + "; ".join(summary_lines)

    summary_entry = {
        "id": 0,
        "timestamp": old[-1]["timestamp"],
        "category": "summary",
        "content": summary[:500],
    }

    return [summary_entry] + keep


def add_memory(repo_root: Path, content: str, category: str = "general") -> dict[str, Any]:
    """Add a memory entry and refresh installed context files."""
    storage = get_storage(repo_root)
    entries = _as_list(storage.read_collection(Collections.MEMORY))
    entry = {
        "id": len(entries) + 1,
        "timestamp": time.time(),
        "category": category,
        "content": content,
    }
    entries.append(entry)
    storage.write_collection(Collections.MEMORY, _compact_memory(entries))
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
    """Recall project memory as a compact markdown document."""
    from .repo_map import CHANGELOG_FILE, has_changes, save_repo_map

    base = mnemo_path(repo_root)
    if not base.exists():
        return ""

    if has_changes(repo_root):
        save_repo_map(repo_root, index=False)

    storage = get_storage(repo_root)
    sections: list[str] = []

    context = dict(_as_dict(storage.read_collection(Collections.CONTEXT)))
    context.pop("last_updated", None)
    if context:
        sections.append("# Project Context")
        for key, value in context.items():
            sections.append(f"- **{key}**: {value}")
        sections.append("")

    decisions = _as_list(storage.read_collection(Collections.DECISIONS))
    if decisions:
        sections.append("# Decisions")
        for decision in decisions:
            reasoning = f" - {decision['reasoning']}" if decision.get("reasoning") else ""
            sections.append(f"- {decision['decision']}{reasoning}")
        sections.append("")

    memory = _as_list(storage.read_collection(Collections.MEMORY))
    if memory:
        sections.append("# Memory")
        for item in memory:
            cat = f" [{item['category']}]" if item.get("category") != "general" else ""
            sections.append(f"- {item['content']}{cat}")
        sections.append("")

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
