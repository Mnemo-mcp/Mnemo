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
