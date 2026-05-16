"""Memory search, recall, and lookup operations."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from ..config import mnemo_path
from ..retrieval import semantic_query, index_chunks
from ..storage import Collections, get_storage

from ._shared import (
    logger,
    MAX_OUTPUT_CHARS,
    MEMORY_TOKEN_BUDGET,
    TOKEN_CHAR_RATIO,
    MEMORY_NAMESPACE,
    _CATEGORY_PATTERNS,
    _as_list,
    _as_dict,
    _get_current_branch,
)
from .retention import _compute_retention, _get_tier, auto_forget_sweep


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


def _increment_recall_counts(repo_root: Path, result_ids: list[str]) -> None:
    """Increment recall_count, access_count, last_recalled, last_accessed_at, and access_history for retrieved memories."""
    if not result_ids:
        return
    storage = get_storage(repo_root)
    entries = _as_list(storage.read_collection(Collections.MEMORY))
    now = time.time()
    changed = False
    for entry in entries:
        mem_id = f"memory-{entry.get('id', 0)}"
        if mem_id in result_ids or str(entry.get("id")) in result_ids:
            entry["recall_count"] = entry.get("recall_count", 0) + 1
            entry["last_recalled"] = now
            entry["access_count"] = entry.get("access_count", 0) + 1
            entry["last_accessed_at"] = now
            history = entry.get("access_history", [])
            history.append(now)
            entry["access_history"] = history[-20:]
            changed = True
    if changed:
        storage.write_collection(Collections.MEMORY, entries)


def search_memory(repo_root: Path, query: str, deep: bool = False, tags: list[str] | None = None) -> str:
    """Search memories semantically, auto-detecting category from query. Optionally filter by tags."""
    category = _infer_search_category(query)
    limit = 15 if deep else 7

    # Zero-LLM query expansion
    entities = re.findall(r'"([^"]+)"', query)
    entities += [w for w in query.split() if w[0:1].isupper() and len(w) > 1]
    entities += re.findall(r'[\w/]+\.\w+', query)
    entities += re.findall(r'[\w]+/[\w/]+', query)
    expanded_query = query + " " + " ".join(entities) if entities else query

    # Semantic search
    filters = {"category": category} if category else None
    semantic_results = semantic_query(repo_root, MEMORY_NAMESPACE, expanded_query, limit=limit, filters=filters)
    if len(semantic_results) < 3:
        unfiltered = semantic_query(repo_root, MEMORY_NAMESPACE, expanded_query, limit=limit)
        seen_ids = {r.get("id") for r in semantic_results}
        for r in unfiltered:
            if r.get("id") not in seen_ids:
                semantic_results.append(r)

    # Keyword search
    storage = get_storage(repo_root)
    entries = _as_list(storage.read_collection(Collections.MEMORY))
    entries = [e for e in entries if not e.get("evicted") and not e.get("superseded_by")]

    if tags:
        entries = [e for e in entries if set(tags) & set(e.get("tags", []))]

    query_lower = query.lower()
    keyword_results = [
        {"id": f"memory-{e.get('id', 0)}", "content": e["content"], "metadata": {"category": e.get("category", "general")}}
        for e in entries if query_lower in e.get("content", "").lower()
    ]

    # RRF fusion
    all_ids: dict[str, dict] = {}
    semantic_rank: dict[str, int] = {}
    keyword_rank: dict[str, int] = {}
    graph_rank: dict[str, int] = {}

    for rank, r in enumerate(semantic_results):
        rid = r.get("id", f"sem-{rank}")
        semantic_rank[rid] = rank
        all_ids[rid] = r

    for rank, r in enumerate(keyword_results):
        rid = r.get("id", f"kw-{rank}")
        keyword_rank[rid] = rank
        if rid not in all_ids:
            all_ids[rid] = r

    # Graph-boosted search (new engine: LadybugDB)
    try:
        from ..engine.memory_graph import graph_boosted_search
        lbug_results = graph_boosted_search(repo_root, query, limit=limit)
        for rank, r in enumerate(lbug_results):
            rid = r.get("id", f"graph-{rank}")
            # Normalize ID format
            if rid.startswith("mem:"):
                rid = f"memory-{rid.replace('mem:', '')}"
            graph_rank[rid] = rank
            if rid not in all_ids:
                all_ids[rid] = {"id": rid, "content": r.get("content", ""), "metadata": {"category": r.get("category", "general")}}
    except Exception:
        pass

    max_rank = limit * 2
    scored = []
    for rid, r in all_ids.items():
        sr = semantic_rank.get(rid, max_rank)
        kr = keyword_rank.get(rid, max_rank)
        gr = graph_rank.get(rid, max_rank)
        rrf = 0.4 / (60 + kr) + 0.6 / (60 + sr) + 0.3 / (60 + gr)
        scored.append((rrf, r))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Source diversification
    cat_counts: dict[str, int] = {}
    results = []
    for _, r in scored:
        cat = r.get("metadata", {}).get("category", "general")
        if cat_counts.get(cat, 0) >= 3:
            continue
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        results.append(r)
        if len(results) >= limit:
            break

    _increment_recall_counts(repo_root, [r.get("id", "") for r in results])

    if not results:
        return f"No memories found for '{query}'."

    lines = [f"# Memory Search: '{query}'\n"]
    for r in results:
        content = r.get("content", "")
        if content.startswith("memory "):
            content = content.split("\n", 1)[-1] if "\n" in content else content
        meta = r.get("metadata", {})
        cat = meta.get("category", "general")
        lines.append(f"- [{cat}] {content}")

    total = len(entries)
    if total > len(results) and not deep:
        lines.append(f"\n*Showing {len(results)} of {total} total memories. Search again with deep=true for more.*")
    return "\n".join(lines)


def lookup(repo_root: Path, query: str) -> str:
    """Look up detailed info for a specific file or folder - parses on demand."""
    # Fast path: try LadybugDB first
    try:
        from ..engine.db import open_db, get_db_path
        if get_db_path(repo_root).exists():
            _, conn = open_db(repo_root)
            # Search for matching classes/functions
            results = []
            r = conn.execute(f"MATCH (c:Class) WHERE c.name CONTAINS '{query}' OR c.file CONTAINS '{query}' RETURN c.name, c.file, c.implements LIMIT 10")
            while r.has_next():
                row = r.get_next()
                results.append(f"**{row[0]}** ({row[1]})" + (f" : {row[2]}" if row[2] else ""))
                # Get methods
                r2 = conn.execute(f"MATCH (c:Class {{name: '{row[0]}'}})-[:HAS_METHOD]->(m:Method) RETURN m.name, m.signature")
                while r2.has_next():
                    mrow = r2.get_next()
                    results.append(f"  {mrow[1][:100]}")

            r = conn.execute(f"MATCH (f:Function) WHERE f.name CONTAINS '{query}' OR f.file CONTAINS '{query}' RETURN f.name, f.file, f.signature LIMIT 10")
            while r.has_next():
                row = r.get_next()
                results.append(f"**{row[0]}** ({row[1]}): {row[2][:80]}")

            if results:
                return f"# Lookup: {query}\n\n" + "\n".join(results)
    except Exception:
        pass

    # Fallback: parse from disk
    from ..repo_map import MAX_FILE_SIZE, SUPPORTED_EXTENSIONS, _extract_file, _should_ignore
    from ..chunking import make_code_chunks

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

    if discovered_chunks:
        try:
            index_chunks(repo_root, "code", discovered_chunks)
        except Exception as exc:
            logger.warning(f"Failed to index discovered chunks: {exc}")

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
    """Recall decisions section (active only, no reasoning)."""
    decisions = [d for d in _as_list(storage.read_collection(Collections.DECISIONS)) if d.get("active", True)]
    if not decisions:
        return ""
    lines = ["# Decisions"]
    for decision in decisions:
        lines.append(f"- {decision['decision']}")
    lines.append("")
    return "\n".join(lines)


# Module-level recall counter (used by _recall_memory for periodic sweep)
_recall_counter = 0


def _recall_memory(repo_root: Path, storage) -> str:
    """Recall memory section — token-budgeted, scored hot memories with eviction and branch awareness."""
    memory = _as_list(storage.read_collection(Collections.MEMORY))

    now = time.time()
    current_branch = _get_current_branch(repo_root)
    hot_memories = []
    archived_count = 0
    changed = False

    for entry in memory:
        if entry.get("evicted"):
            archived_count += 1
            continue
        retention = _compute_retention(entry, now)
        age_days = (now - entry.get("timestamp", now)) / 86400
        if retention < 0.1 and age_days > 60:
            entry["evicted"] = True
            archived_count += 1
            changed = True
            continue
        tier = _get_tier(entry, now)
        if tier == "hot":
            hot_memories.append(entry)
        else:
            branch = entry.get("branch", "main")
            if branch in (current_branch, "main", "master") or retention >= 0.5:
                if tier == "warm":
                    hot_memories.append(entry)
                else:
                    archived_count += 1
            else:
                archived_count += 1

    if changed:
        storage.write_collection(Collections.MEMORY, memory)

    if not hot_memories and archived_count == 0:
        return ""

    from .retention import summarize_for_injection

    # Split: last session (<24h) vs earlier
    cutoff = now - 86400
    recent = [e for e in hot_memories if e.get("timestamp", 0) >= cutoff]
    earlier = [e for e in hot_memories if e.get("timestamp", 0) < cutoff]

    recent.sort(key=lambda e: e.get("timestamp", 0), reverse=True)

    CATEGORY_WEIGHTS = {'architecture': 0.9, 'preference': 0.85, 'decision': 0.9, 'pattern': 0.8, 'bug': 0.7, 'general': 0.5, 'todo': 0.6}

    def _score(entry):
        cat = entry.get("category", "general")
        importance = CATEGORY_WEIGHTS.get(cat, 0.5)
        days = (now - entry.get("timestamp", now)) / 86400
        recency = 1.0 - min(days / 30, 1.0)
        ac = entry.get("access_count", 0)
        frequency = min(ac / 10, 1.0)
        return recency * 0.5 + importance * 0.3 + frequency * 0.2

    earlier.sort(key=_score, reverse=True)

    char_budget = MEMORY_TOKEN_BUDGET * TOKEN_CHAR_RATIO
    lines = []
    used_chars = 0
    included = 0

    if recent:
        lines.append("# Memory (Last Session)")
        for item in recent:
            cat = f" [{item['category']}]" if item.get("category") != "general" else ""
            line = f"- {item['content']}{cat}"
            if used_chars + len(line) > char_budget:
                break
            lines.append(line)
            used_chars += len(line)
            included += 1

    if earlier:
        lines.append("\n# Earlier (concise)")
        for item in earlier:
            line = f"- {summarize_for_injection(item)}"
            if used_chars + len(line) > char_budget:
                break
            lines.append(line)
            used_chars += len(line)
            included += 1

    excluded = len(hot_memories) - included + archived_count
    if excluded > 0:
        lines.append(
            f"\n*{excluded} more memories excluded (budget/archived)"
            f" — use mnemo_search_memory to find specific context.*"
        )
    lines.append("")
    return "\n".join(lines)


def _recall_active_task(repo_root: Path, storage) -> str:
    """Recall active plan/task context from plans.json."""
    from ..plan import _load_plans

    plans = _load_plans(repo_root)
    active = [p for p in plans if p.get("status") in (None, "active", "in_progress")]
    if not active:
        return ""

    plan = active[-1]
    lines = ["# Active Plan"]
    lines.append(f"- **{plan.get('id', '')}**: {plan.get('title', '')}")

    tasks = plan.get("tasks", [])
    done = [t for t in tasks if t.get("status") == "done"]
    pending = [t for t in tasks if t.get("status") != "done"]

    if done:
        lines.append(f"- Completed: {len(done)}/{len(tasks)}")
    if pending:
        next_task = pending[0]
        lines.append(f"- Next: {next_task.get('id', '')} — {next_task.get('title', next_task.get('description', ''))}")

    lines.append("")
    return "\n".join(lines)


def _recall_recent_changes(base: Path) -> str:
    """Recall recent changes section."""
    from ..repo_map import CHANGELOG_FILE
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
    """Recall repo map section using compact tree."""
    tree_path = base / "tree.md"
    if not tree_path.exists():
        return ""
    try:
        content = tree_path.read_text(encoding="utf-8")
        budget = max(500, 2000 - header_size)
        if len(content) > budget:
            content = content[:budget - 3] + "..."
        return f"# Repo Map\n```\n{content}\n```\n"
    except OSError:
        return ""


def recall(repo_root: Path, tier: str = "standard") -> str:
    """Recall project memory with tiered retrieval."""
    global _recall_counter
    _recall_counter += 1

    base = mnemo_path(repo_root)
    if not base.exists():
        return ""

    # Periodic maintenance (every 10th recall)
    if _recall_counter % 10 == 0:
        from ..corrections import decay_corrections
        decay_corrections(repo_root)
        try:
            auto_forget_sweep(repo_root)
        except Exception:
            pass

    if tier == "compact":
        return _recall_compact(repo_root)

    storage = get_storage(repo_root)

    if tier == "deep":
        return _recall_deep(repo_root, base, storage)

    # tier == "standard": budgeted ~2000 tokens
    return _recall_standard(repo_root, base, storage)


def _recall_compact(repo_root: Path) -> str:
    """Compact tier (~500 tokens): task + 3 memories + plan step + 1 warning."""
    from .retention import summarize_for_injection
    from ..plan import _load_plans
    from ..regressions import _load_regressions

    storage = get_storage(repo_root)
    parts: list[str] = []

    # Active task
    tasks = _as_list(storage.read_collection(Collections.TASKS))
    active = [t for t in tasks if t.get("status") == "active"]
    if active:
        t = active[-1]
        parts.append(f"Task: {t.get('task_id', '')} {t.get('description', '')}")

    # 3 most relevant hot memories
    memory = _as_list(storage.read_collection(Collections.MEMORY))
    now = time.time()
    hot = [e for e in memory if not e.get("evicted") and _get_tier(e, now) == "hot"]
    hot.sort(key=lambda e: _compute_retention(e, now), reverse=True)
    for entry in hot[:3]:
        parts.append(summarize_for_injection(entry))

    # Next plan step
    plans = _load_plans(repo_root)
    for plan in plans:
        for task in plan.get("tasks", []):
            if task.get("status") in (None, "pending", "todo"):
                parts.append(f"Next: {task.get('title', task.get('description', ''))}")
                break
        else:
            continue
        break

    # 1 warning (regression)
    regressions = _load_regressions(repo_root)
    if regressions:
        r = regressions[-1]
        parts.append(f"⚠️ Regression risk: {r.get('file', '')} — {r.get('bug', '')[:60]}")

    return "\n".join(parts)


def _recall_standard(repo_root: Path, base: Path, storage) -> str:
    """Standard tier (~2000 tokens): budgeted recall, max 10 memories, truncated map."""
    from ..repo_map.identity import format_identity
    from .slots import get_working_context, reflect_slots
    import mnemo.memory.slots as _slots_mod

    sections = [
        _recall_context(storage),
        format_identity(repo_root),
        _recall_decisions(storage),
    ]

    _slots_mod._recall_counter += 1
    if _slots_mod._recall_counter % 5 == 0:
        reflect_slots(repo_root)
    working_ctx = get_working_context(repo_root)
    if working_ctx:
        sections.append(f"# Working Context\n{working_ctx}\n")

    # Memory — capped at 10 entries
    memory = _as_list(storage.read_collection(Collections.MEMORY))
    now = time.time()
    current_branch = _get_current_branch(repo_root)
    hot_memories = []
    for entry in memory:
        if entry.get("evicted"):
            continue
        tier_val = _get_tier(entry, now)
        if tier_val in ("hot", "warm"):
            branch = entry.get("branch", "main")
            if branch in (current_branch, "main", "master") or _compute_retention(entry, now) >= 0.5:
                hot_memories.append(entry)

    CATEGORY_WEIGHTS = {'architecture': 0.9, 'preference': 0.85, 'decision': 0.9, 'pattern': 0.8, 'bug': 0.7, 'general': 0.5, 'todo': 0.6}

    def _score_std(entry):
        cat = entry.get("category", "general")
        importance = CATEGORY_WEIGHTS.get(cat, 0.5)
        days = (now - entry.get("timestamp", now)) / 86400
        recency = 1.0 - min(days / 30, 1.0)
        ac = entry.get("access_count", 0)
        frequency = min(ac / 10, 1.0)
        return recency * 0.5 + importance * 0.3 + frequency * 0.2

    from .retention import summarize_for_injection

    cutoff = now - 86400
    recent = [e for e in hot_memories if e.get("timestamp", 0) >= cutoff]
    earlier = [e for e in hot_memories if e.get("timestamp", 0) < cutoff]

    recent.sort(key=lambda e: e.get("timestamp", 0), reverse=True)
    earlier.sort(key=_score_std, reverse=True)

    # Cap total at 10
    recent = recent[:10]
    remaining = max(10 - len(recent), 0)
    earlier = earlier[:remaining]

    if recent or earlier:
        lines = []
        if recent:
            lines.append("# Memory (Last Session)")
            for item in recent:
                cat = f" [{item['category']}]" if item.get("category") != "general" else ""
                lines.append(f"- {item['content']}{cat}")
        if earlier:
            lines.append("\n# Earlier (concise)")
            for item in earlier:
                lines.append(f"- {summarize_for_injection(item)}")
        lines.append("")
        sections.append("\n".join(lines))

    sections.append(_recall_active_task(repo_root, storage))
    sections.append(_recall_recent_changes(base))

    # Repo map — truncated to fit ~2000 token total budget
    header = "\n".join(s for s in sections if s)
    budget_chars = 2000 * TOKEN_CHAR_RATIO
    remaining = max(budget_chars - len(header), 200)
    repo_map = _recall_repo_map(base, len(header))
    if len(repo_map) > remaining:
        repo_map = repo_map[:remaining - 3] + "..."
    sections.append(repo_map)

    return "\n".join(s for s in sections if s)


def _recall_deep(repo_root: Path, base: Path, storage) -> str:
    """Deep tier (unlimited): full recall, no truncation."""
    from ..repo_map.identity import format_identity
    from .slots import get_working_context, reflect_slots
    import mnemo.memory.slots as _slots_mod

    sections = [
        _recall_context(storage),
        format_identity(repo_root),
        _recall_decisions(storage),
    ]

    _slots_mod._recall_counter += 1
    if _slots_mod._recall_counter % 5 == 0:
        reflect_slots(repo_root)
    working_ctx = get_working_context(repo_root)
    if working_ctx:
        sections.append(f"# Working Context\n{working_ctx}\n")

    sections += [
        _recall_memory(repo_root, storage),
        _recall_active_task(repo_root, storage),
        _recall_recent_changes(base),
        _recall_repo_map(base, 0),
    ]

    return "\n".join(s for s in sections if s)
