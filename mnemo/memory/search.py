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
    entries = [e for e in entries if not e.get("evicted")]

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

    # Graph-boosted search
    try:
        from ..graph.local import LocalGraph
        graph = LocalGraph(repo_root)
        if graph.exists():
            entity_names = set()
            for r in list(semantic_results) + keyword_results:
                content = r.get("content", "")
                entity_names.update(w for w in re.findall(r'\b[A-Z][a-zA-Z]{3,}\b', content))
            graph_results = []
            for entity in list(entity_names)[:10]:
                nodes = graph.find_nodes(name_pattern=entity)
                for node in nodes[:3]:
                    neighbors = graph.get_neighbors(node.id, direction="both")
                    for edge, neighbor in neighbors:
                        if neighbor.type in ("memory", "decision"):
                            mem_id_str = neighbor.id
                            if mem_id_str.startswith("memory:"):
                                rid = f"memory-{mem_id_str.split(':',1)[1]}"
                            else:
                                rid = mem_id_str
                            if rid not in graph_results:
                                graph_results.append(rid)
            for rank, rid in enumerate(graph_results):
                graph_rank[rid] = rank
                if rid not in all_ids:
                    mid = rid.replace("memory-", "")
                    for e in entries:
                        if str(e.get("id")) == mid:
                            all_ids[rid] = {"id": rid, "content": e["content"], "metadata": {"category": e.get("category", "general")}}
                            break
    except Exception as exc:
        logger.debug(f"Vector search fallback: {exc}")

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
    global _recall_counter
    _recall_counter += 1
    if _recall_counter % 10 == 0:
        try:
            auto_forget_sweep(repo_root)
        except Exception as exc:
            logger.debug(f"Auto-forget sweep failed: {exc}")

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

    CATEGORY_WEIGHTS = {'architecture': 0.9, 'preference': 0.85, 'decision': 0.9, 'pattern': 0.8, 'bug': 0.7, 'general': 0.5, 'todo': 0.6}

    def _score(entry):
        cat = entry.get("category", "general")
        importance = CATEGORY_WEIGHTS.get(cat, 0.5)
        days = (now - entry.get("timestamp", now)) / 86400
        recency = 1.0 - min(days / 30, 1.0)
        ac = entry.get("access_count", 0)
        frequency = min(ac / 10, 1.0)
        return importance * 0.5 + recency * 0.3 + frequency * 0.2

    hot_memories.sort(key=_score, reverse=True)

    char_budget = MEMORY_TOKEN_BUDGET * TOKEN_CHAR_RATIO
    lines = []
    included = 0
    used_chars = 0
    if hot_memories:
        lines.append("# Memory")
        for item in hot_memories:
            cat = f" [{item['category']}]" if item.get("category") != "general" else ""
            line = f"- {item['content']}{cat}"
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
    """Recall repo map section using compact tree + graph summary."""
    graph_summary = ""
    graph_path = base / "graph.json"
    if graph_path.exists():
        try:
            from ..graph.local import LocalGraph
            graph = LocalGraph(base.parent)
            s = graph.stats()
            node_types = s.get("node_types", {})
            top_types = sorted(node_types.items(), key=lambda x: x[1], reverse=True)[:5]
            graph_summary = f"Knowledge Graph: {s['nodes']} nodes, {s['edges']} edges ({', '.join(f'{c} {t}' for t, c in top_types)})\n"
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
        except Exception as exc:
            logger.debug(f"Graph summary generation failed: {exc}")

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


def _index_changed_files(repo_root: Path, old_hashes: dict[str, Any]) -> None:
    """Incrementally index only files that changed since last hash snapshot."""
    from ..repo_map import _extract_file, _should_ignore, MAX_FILE_SIZE
    from ..config import SUPPORTED_EXTENSIONS
    from ..chunking import make_code_chunks
    import hashlib

    chunks = []
    for ext, language in SUPPORTED_EXTENSIONS.items():
        for filepath in repo_root.rglob(f"*{ext}"):
            if _should_ignore(filepath) or filepath.stat().st_size > MAX_FILE_SIZE:
                continue
            rel = str(filepath.relative_to(repo_root))
            try:
                content = filepath.read_bytes()
                current_hash = hashlib.md5(content, usedforsecurity=False).hexdigest()
            except (OSError, PermissionError):
                continue
            if old_hashes.get(rel) == current_hash:
                continue
            info = _extract_file(content, language)
            if info:
                chunks.extend(make_code_chunks(rel, language, info))

    if chunks:
        try:
            index_chunks(repo_root, "code", chunks)
        except Exception as exc:
            logger.warning(f"Failed to index changed files: {exc}")


def recall(repo_root: Path) -> str:
    """Recall project memory with token-budgeted tiered retrieval."""
    from ..repo_map import has_changes, save_repo_map
    from ..repo_map.identity import format_identity
    from ..corrections import decay_corrections

    base = mnemo_path(repo_root)
    if not base.exists():
        return ""

    decay_corrections(repo_root)

    if has_changes(repo_root):
        old_hashes = _as_dict(get_storage(repo_root).read_collection(Collections.HASHES))
        save_repo_map(repo_root, index=False)
        _index_changed_files(repo_root, old_hashes)

    storage = get_storage(repo_root)
    sections = [
        _recall_context(storage),
        format_identity(repo_root),
        _recall_decisions(storage),
    ]

    from .slots import get_working_context, reflect_slots
    import mnemo.memory.slots as _slots_mod
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
    ]
    header = "\n".join(s for s in sections if s)
    sections.append(_recall_repo_map(base, len(header)))

    return "\n".join(s for s in sections if s)
