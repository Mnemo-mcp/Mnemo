"""Middleware pipeline for MCP tool calls — dedup, metrics, observations, enrichment."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

from .utils.dedup import _dedup
from .utils.metrics import record_call
from .utils.observations import record_observation
from .enrichment import enrich_response


def apply_middleware(
    tool_name: str,
    arguments: dict,
    repo_root: Path,
    handler: Callable[[Path, dict], str],
) -> str:
    """Run handler with dedup check, metrics, observation recording, and enrichment."""
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

    # Enrich
    return enrich_response(repo_root, tool_name, result, arguments)
