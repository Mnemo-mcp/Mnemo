"""Observation capture — records tool usage for session awareness."""

from __future__ import annotations

import json
import time
from pathlib import Path

from ..config import mnemo_path

OBSERVATIONS_FILE = "observations.json"
MAX_OBSERVATIONS = 500


def record_observation(repo_root: Path, tool_name: str, tool_input_summary: str, tool_output_summary: str, session_id: str = '') -> None:
    """Record a tool invocation observation."""

    obs = _load_observations(repo_root)
    obs.append({
        "timestamp": time.time(),
        "tool_name": tool_name,
        "input_summary": tool_input_summary[:200],
        "output_summary": tool_output_summary[:200],
        "session_id": session_id,
    })
    if len(obs) > MAX_OBSERVATIONS:
        obs = obs[-MAX_OBSERVATIONS:]
    _save_observations(repo_root, obs)


def get_recent_observations(repo_root: Path, limit: int = 20) -> list:
    """Return the most recent observations."""
    obs = _load_observations(repo_root)
    return obs[-limit:]


def _load_observations(repo_root: Path) -> list:
    path = mnemo_path(repo_root) / OBSERVATIONS_FILE
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_observations(repo_root: Path, obs: list) -> None:
    path = mnemo_path(repo_root) / OBSERVATIONS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obs, indent=2) + "\n", encoding="utf-8")


# --- Context dedup (MNO-023) ---

_injected_sessions: dict[str, tuple[float, set[int]]] = {}
_SESSION_TTL = 3600  # 1 hour — reset on agentSpawn


def mark_injected(repo_root: Path, memory_id: int) -> None:
    """Mark a memory ID as already injected this session."""
    key = str(repo_root)
    _, ids = _injected_sessions.get(key, (time.time(), set()))
    ids.add(memory_id)
    _injected_sessions[key] = (time.time(), ids)


def was_injected(repo_root: Path, memory_id: int) -> bool:
    """Check if a memory was already injected this session."""
    key = str(repo_root)
    entry = _injected_sessions.get(key)
    if not entry:
        return False
    ts, ids = entry
    if time.time() - ts > _SESSION_TTL:
        _injected_sessions.pop(key, None)
        return False
    return memory_id in ids


def reset_injection_session(repo_root: Path) -> None:
    """Reset the injection session (called on agentSpawn)."""
    _injected_sessions.pop(str(repo_root), None)


# --- Observation Mining (MNO-025) ---


def mine_patterns(repo_root: Path) -> list[str]:
    """Analyze observations for repeated searches and common tool sequences."""
    from collections import Counter

    obs = _load_observations(repo_root)
    if not obs:
        return []

    patterns: list[str] = []

    # Detect repeated searches (same topic >3 times)
    search_inputs: list[str] = []
    for o in obs:
        if "search" in o.get("tool_name", ""):
            search_inputs.append(o.get("input_summary", ""))

    input_counts = Counter(search_inputs)
    for query, count in input_counts.most_common(5):
        if count > 3:
            patterns.append(f"Frequently searched ({count}x): {query[:80]}")

    # Detect common tool sequences (pairs)
    if len(obs) >= 2:
        pairs = Counter()
        for i in range(len(obs) - 1):
            pair = (obs[i].get("tool_name", ""), obs[i + 1].get("tool_name", ""))
            pairs[pair] += 1
        for (a, b), count in pairs.most_common(3):
            if count > 3:
                patterns.append(f"Common sequence ({count}x): {a} → {b}")

    # MNO-027: Auto-slot detection
    try:
        from ..memory.slots import detect_frequent_topics
        detect_frequent_topics(repo_root)
    except Exception:
        pass

    return patterns
