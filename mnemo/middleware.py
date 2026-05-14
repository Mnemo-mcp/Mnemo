"""Middleware pipeline for MCP tool calls — dedup, metrics, observations, enrichment."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

from .utils.dedup import _dedup
from .utils.metrics import record_call
from .utils.observations import record_observation, get_recent_observations
from .enrichment import enrich_response

_call_count: int = 0
_SUMMARIZE_EVERY = 5
_MINE_EVERY = 50


def _session_summarize(repo_root: Path) -> None:
    """Summarize recent activity and store as working memory (MNO-015)."""
    from .memory.store import add_memory
    obs = get_recent_observations(repo_root, limit=_SUMMARIZE_EVERY)
    if not obs:
        return
    tools_used = [o.get("tool_name", "") for o in obs]
    summary = f"Session activity: called {', '.join(tools_used)}"
    entry = add_memory(repo_root, summary[:300], category="general", source="session_summarizer")
    # Set forget_after to 24h from now
    if entry and isinstance(entry, dict):
        from .storage import Collections, get_storage
        storage = get_storage(repo_root)
        entries = storage.read_collection(Collections.MEMORY)
        if isinstance(entries, list):
            for e in entries:
                if e.get("id") == entry.get("id"):
                    e["tier"] = "working"
                    e["forget_after"] = time.time() + 86400
                    break
            storage.write_collection(Collections.MEMORY, entries)


def apply_middleware(
    tool_name: str,
    arguments: dict,
    repo_root: Path,
    handler: Callable[[Path, dict], str],
) -> str:
    """Run handler with dedup check, metrics, observation recording, and enrichment."""
    global _call_count

    # Dedup — skip for recall-type tools that should always return fresh data
    _NO_DEDUP = {"mnemo_recall", "mnemo_context_for_task", "mnemo_plan"}
    tool_input = json.dumps(arguments, sort_keys=True, default=str)
    if tool_name not in _NO_DEDUP and _dedup.is_duplicate(tool_name, tool_input):
        return "Duplicate call skipped (same input within 5 minutes)."

    # Execute
    t0 = time.time()
    try:
        result = handler(repo_root, arguments)
        record_call(tool_name, time.time() - t0, success=True)
    except Exception:
        record_call(tool_name, time.time() - t0, success=False)
        raise

    # Observe
    record_observation(repo_root, tool_name, tool_input[:200], (result or "")[:200])

    # Session summarization (MNO-015)
    _call_count += 1
    if _call_count % _SUMMARIZE_EVERY == 0:
        try:
            _session_summarize(repo_root)
        except Exception:
            pass

    # Observation mining (MNO-025)
    if _call_count % _MINE_EVERY == 0:
        try:
            from .utils.observations import mine_patterns
            from .memory.lessons import add_lesson
            for pattern in mine_patterns(repo_root):
                add_lesson(repo_root, pattern, source="observation_mining")
        except Exception:
            pass

    # Enrich
    return enrich_response(repo_root, tool_name, result, arguments)
