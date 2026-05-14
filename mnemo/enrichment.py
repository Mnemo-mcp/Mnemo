"""Response enrichment — injects proactive context into tool responses."""

from __future__ import annotations

from pathlib import Path

from .utils.logger import get_logger

logger = get_logger("enrichment")


def enrich_response(repo_root: Path, tool_name: str, result: str, arguments: dict) -> str:
    """Append proactive hints to a tool response based on what Mnemo knows."""
    # Skip enrichment for these tools (they're already meta/context tools)
    SKIP_TOOLS = {"mnemo_recall", "mnemo_plan", "mnemo_graph"}
    if tool_name in SKIP_TOOLS:
        return result

    hints = []

    try:
        hints.extend(_plan_hints(repo_root, tool_name, result, arguments))
        hints.extend(_regression_hints(repo_root, tool_name, arguments))
        hints.extend(_incident_hints(repo_root, tool_name, arguments))
        hints.extend(_decision_hints(repo_root, tool_name, arguments))
        hints.extend(_correction_hints(repo_root, tool_name, arguments))
        hints.extend(_self_verify_hints(repo_root, tool_name, arguments))
    except Exception as exc:
        # Enrichment is non-fatal — never break the actual response
        logger.debug(f"Enrichment error: {exc}")

    if not hints:
        return result

    return result + "\n\n---\n**Mnemo notes:**\n" + "\n".join(f"- {h}" for h in hints)


def _plan_hints(repo_root: Path, tool_name: str, result: str, arguments: dict) -> list[str]:
    """Surface active plan next task."""
    try:
        from mnemo.plan import get_active_plan_hint, auto_detect_completion
    except ImportError:
        return []

    hints = []

    # Auto-detect plan completion from mnemo_remember content
    if tool_name == "mnemo_remember":
        content = arguments.get("content", "")
        if content:
            auto_result = auto_detect_completion(repo_root, content)
            if auto_result:
                hints.append(auto_result)

    # Show next task hint (but not on every call — only on "work" tools)
    WORK_TOOLS = {"mnemo_remember", "mnemo_lookup", "mnemo_similar", "mnemo_map",
                  "mnemo_commit_message", "mnemo_task_done", "mnemo_dead_code",
                  "mnemo_health", "mnemo_intelligence"}
    if tool_name in WORK_TOOLS:
        hint = get_active_plan_hint(repo_root)
        if hint:
            hints.append(hint)

    return hints


def _regression_hints(repo_root: Path, tool_name: str, arguments: dict) -> list[str]:
    """Warn about regression risks on files being looked up."""
    if tool_name not in ("mnemo_lookup", "mnemo_graph", "mnemo_who_touched"):
        return []

    query = arguments.get("query", "") or arguments.get("node", "")
    if not query:
        return []

    try:
        from mnemo.regressions import _load_regressions
        regressions = _load_regressions(repo_root)
        if not regressions:
            return []

        hits = []
        query_lower = query.lower()
        for reg in regressions:
            if query_lower in reg.get("file", "").lower() or query_lower in reg.get("bug", "").lower():
                hits.append(f"\u26a0\ufe0f Regression risk on `{reg['file']}`: {reg['bug']}")
        return hits[:2]
    except (ImportError, Exception):
        return []


def _incident_hints(repo_root: Path, tool_name: str, arguments: dict) -> list[str]:
    """Surface related incidents when looking at code (MNO-835 recommendation engine)."""
    if tool_name not in ("mnemo_lookup", "mnemo_similar"):
        return []

    query = arguments.get("query", "")
    if not query:
        return []

    try:
        from mnemo.incidents import _load_incidents
        incidents = _load_incidents(repo_root)
        if not incidents:
            return []

        query_lower = query.lower()
        hits = []
        for inc in incidents:
            searchable = (inc.get("title", "") + " " + " ".join(inc.get("services", []))).lower()
            if any(w in searchable for w in query_lower.split() if len(w) > 3):
                hits.append(f"\U0001f6a8 Related incident: {inc.get('title', '')[:80]} (fix: {inc.get('fix', '')[:60]})")
        return hits[:1]
    except (ImportError, Exception):
        return []


def _decision_hints(repo_root: Path, tool_name: str, arguments: dict) -> list[str]:
    """Surface related decisions when looking at code."""
    if tool_name not in ("mnemo_lookup", "mnemo_similar", "mnemo_graph", "mnemo_intelligence"):
        return []

    query = arguments.get("query", "") or arguments.get("node", "")
    if not query:
        return []

    try:
        from mnemo.storage import Collections, get_storage
        storage = get_storage(repo_root)
        decisions = storage.read_collection(Collections.DECISIONS)
        if not isinstance(decisions, list) or not decisions:
            return []

        query_lower = query.lower()
        hits = []
        for d in decisions:
            text = d.get("decision", "").lower()
            if query_lower in text or any(w in text for w in query_lower.split() if len(w) > 3):
                hits.append(f"\U0001f4cc Decision: {d['decision'][:100]}")
        return hits[:1]
    except (ImportError, Exception):
        return []


def _correction_hints(repo_root: Path, tool_name: str, arguments: dict) -> list[str]:
    """Surface relevant past corrections when the agent is generating suggestions or looking at code."""
    CORRECTION_TOOLS = {
        "mnemo_lookup", "mnemo_similar", "mnemo_remember", "mnemo_intelligence",
        "mnemo_commit_message", "mnemo_pr_description", "mnemo_decide",
        "mnemo_search_memory", "mnemo_context_for_task",
    }
    if tool_name not in CORRECTION_TOOLS:
        return []

    query = arguments.get("query", "") or arguments.get("content", "") or arguments.get("decision", "")
    if not query:
        return []

    try:
        from mnemo.corrections import _load_corrections
        corrections = _load_corrections(repo_root)
        if not corrections:
            return []

        query_lower = query.lower()
        query_words = [w for w in query_lower.split() if len(w) > 3]
        hits = []
        for c in corrections:
            context = (c.get("context", "") + " " + c.get("file", "") + " " + c.get("suggestion", "")).lower()
            if any(w in context for w in query_words):
                hits.append(f"\u26a0\ufe0f Past correction: \"{c.get('suggestion', '')[:60]}\" → \"{c.get('correction', '')[:60]}\"")
        return hits[:2]
    except (ImportError, Exception):
        return []


def _self_verify_hints(repo_root: Path, tool_name: str, arguments: dict) -> list[str]:
    """Warn if new memory/decision contradicts existing decisions (MNO-026)."""
    if tool_name not in ("mnemo_remember", "mnemo_decide"):
        return []

    content = arguments.get("content", "") or arguments.get("decision", "")
    if not content:
        return []

    try:
        from .storage import Collections, get_storage
        from .memory._shared import _text_similarity

        storage = get_storage(repo_root)
        decisions = storage.read_collection(Collections.DECISIONS)
        if not isinstance(decisions, list):
            return []

        hits = []
        for d in decisions:
            if not d.get("active", True):
                continue
            sim = _text_similarity(content, d.get("decision", ""))
            if 0.5 <= sim <= 0.85:
                hits.append(f"⚠️ May contradict Decision #{d['id']}: {d['decision'][:80]}")
        return hits[:2]
    except (ImportError, Exception):
        return []
