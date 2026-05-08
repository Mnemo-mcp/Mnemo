"""Persistent memory store for decisions, context, and notes."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .config import mnemo_path, MEMORY_FILE, DECISIONS_FILE, CONTEXT_FILE, REPO_MAP_FILE

MAX_OUTPUT_CHARS = 75000  # Hard limit for MCP response
RECALL_BUDGET = 12000  # Target: keep recall small (~3K tokens)


def _load_json(path: Path) -> list[dict[str, Any]] | dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text())
    return []


def _save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2))


def _refresh_rule(repo_root: Path):
    """Update the .amazonq/rules/mnemo.md with latest context."""
    from .init import _build_rule_with_context
    rules_dir = repo_root / ".amazonq" / "rules"
    rule_file = rules_dir / "mnemo.md"
    if rule_file.exists():
        rule_file.write_text(_build_rule_with_context(repo_root))


MAX_MEMORY_ENTRIES = 50  # Keep last 50 entries, summarize older ones


def _compact_memory(entries: list[dict]) -> list[dict]:
    """When memory exceeds limit, compress old entries into a summary."""
    if len(entries) <= MAX_MEMORY_ENTRIES:
        return entries

    # Keep the last 30 entries as-is
    keep = entries[-30:]

    # Summarize the older ones into a single entry
    old = entries[:-30]
    summary_lines = [e["content"] for e in old[-20:]]  # Last 20 of the old batch
    summary = "Previous context: " + "; ".join(summary_lines)

    summary_entry = {
        "id": 0,
        "timestamp": old[-1]["timestamp"],
        "category": "summary",
        "content": summary[:500],  # Cap at 500 chars
    }

    return [summary_entry] + keep


def add_memory(repo_root: Path, content: str, category: str = "general") -> dict:
    """Add a memory entry and refresh the rule file."""
    path = mnemo_path(repo_root) / MEMORY_FILE
    entries = _load_json(path)
    if not isinstance(entries, list):
        entries = []
    entry = {
        "id": len(entries) + 1,
        "timestamp": time.time(),
        "category": category,
        "content": content,
    }
    entries.append(entry)
    entries = _compact_memory(entries)
    _save_json(path, entries)
    _refresh_rule(repo_root)
    return entry


def add_decision(repo_root: Path, decision: str, reasoning: str = "") -> dict:
    """Record a decision and refresh the rule file."""
    path = mnemo_path(repo_root) / DECISIONS_FILE
    entries = _load_json(path)
    if not isinstance(entries, list):
        entries = []
    entry = {
        "id": len(entries) + 1,
        "timestamp": time.time(),
        "decision": decision,
        "reasoning": reasoning,
    }
    entries.append(entry)
    _save_json(path, entries)
    _refresh_rule(repo_root)
    return entry


def save_context(repo_root: Path, context: dict[str, Any]) -> None:
    """Save project context and refresh the rule file."""
    path = mnemo_path(repo_root) / CONTEXT_FILE
    existing = {}
    if path.exists():
        existing = json.loads(path.read_text())
    existing.update(context)
    existing["last_updated"] = time.time()
    path.write_text(json.dumps(existing, indent=2))
    _refresh_rule(repo_root)



def lookup(repo_root: Path, query: str) -> str:
    """Look up detailed info for a specific file or folder — parses on demand."""
    from .repo_map import _extract_file, _should_ignore, SUPPORTED_EXTENSIONS, MAX_FILE_SIZE

    query_lower = query.lower().strip("/")
    matches: list[tuple[str, dict]] = []

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
            for m in cls.get("methods", []):
                lines.append(f"- {m}")
        for f in info.get("functions", []):
            lines.append(f"- {f}")
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
    from .repo_map import generate_summary, has_changes, save_summary

    base = mnemo_path(repo_root)
    if not base.exists():
        return ""

    # Only regenerate if files changed
    if has_changes(repo_root):
        save_summary(repo_root)

    sections = []

    # Project context
    context_path = base / CONTEXT_FILE
    if context_path.exists():
        ctx = json.loads(context_path.read_text())
        ctx.pop("last_updated", None)
        if ctx:
            sections.append("# Project Context")
            for k, v in ctx.items():
                sections.append(f"- **{k}**: {v}")
            sections.append("")

    # Decisions
    decisions_path = base / DECISIONS_FILE
    if decisions_path.exists():
        decisions = json.loads(decisions_path.read_text())
        if decisions:
            sections.append("# Decisions")
            for d in decisions:
                reasoning = f" — {d['reasoning']}" if d.get("reasoning") else ""
                sections.append(f"- {d['decision']}{reasoning}")
            sections.append("")

    # Memory
    memory_path = base / MEMORY_FILE
    if memory_path.exists():
        memory = json.loads(memory_path.read_text())
        if memory:
            sections.append("# Memory")
            for m in memory:
                cat = f" [{m['category']}]" if m.get("category") != "general" else ""
                sections.append(f"- {m['content']}{cat}")
            sections.append("")

    # Recent changes
    from .repo_map import CHANGELOG_FILE
    changelog_path = base / CHANGELOG_FILE
    if changelog_path.exists():
        changelog = json.loads(changelog_path.read_text())
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
                        sections.append(f"- Renamed: {old} → {new}")
            sections.append("")

    # Compact repo summary
    summary_path = base / "summary.md"
    if summary_path.exists():
        summary = summary_path.read_text()
        sections.append("# Repo Map")
        sections.append("(use mnemo_lookup for method-level details)\n")
        # Truncate if needed
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
