"""Engineering Episodes — connected problem→decision→fix→outcome stories (MNO-841-843)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ..config import mnemo_path

EPISODES_FILE = "episodes.json"

# Time window for auto-grouping related items into same episode (seconds)
EPISODE_WINDOW = 300  # 5 minutes


def _load_episodes(repo_root: Path) -> list[dict[str, Any]]:
    path = mnemo_path(repo_root) / EPISODES_FILE
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_episodes(repo_root: Path, episodes: list[dict[str, Any]]) -> None:
    path = mnemo_path(repo_root) / EPISODES_FILE
    path.write_text(json.dumps(episodes, indent=2) + "\n", encoding="utf-8")


def _next_episode_id(episodes: list[dict]) -> str:
    max_num = 0
    for ep in episodes:
        eid = ep.get("id", "")
        if eid.startswith("EP-"):
            try:
                max_num = max(max_num, int(eid[3:]))
            except ValueError:
                pass
    return f"EP-{max_num + 1:03d}"


def get_active_episode(repo_root: Path) -> dict[str, Any] | None:
    """Get the most recent active episode (within time window)."""
    episodes = _load_episodes(repo_root)
    now = time.time()
    for ep in reversed(episodes):
        if ep.get("status") == "active" and now - ep.get("last_updated", 0) < EPISODE_WINDOW:
            return ep
    return None


def start_episode(repo_root: Path, title: str, problem: str = "") -> dict[str, Any]:
    """Start a new engineering episode."""
    episodes = _load_episodes(repo_root)
    episode = {
        "id": _next_episode_id(episodes),
        "title": title,
        "status": "active",
        "created": time.time(),
        "last_updated": time.time(),
        "problem": problem,
        "items": [],
    }
    episodes.append(episode)
    _save_episodes(repo_root, episodes)
    return episode


def add_to_episode(repo_root: Path, item_type: str, item_id: str, content: str) -> str | None:
    """Add an item to the active episode. Auto-creates episode if none active."""
    episodes = _load_episodes(repo_root)
    now = time.time()

    # Find active episode
    active = None
    for ep in reversed(episodes):
        if ep.get("status") == "active" and now - ep.get("last_updated", 0) < EPISODE_WINDOW:
            active = ep
            break

    if not active:
        return None  # No active episode, caller can decide to create one

    active["items"].append({
        "type": item_type,
        "id": item_id,
        "content": content[:200],
        "timestamp": now,
    })
    active["last_updated"] = now
    _save_episodes(repo_root, episodes)
    return active["id"]


def close_episode(repo_root: Path, episode_id: str, outcome: str = "") -> str:
    """Close an episode with an outcome summary."""
    episodes = _load_episodes(repo_root)
    for ep in episodes:
        if ep["id"] == episode_id:
            ep["status"] = "closed"
            ep["outcome"] = outcome
            ep["closed_at"] = time.time()
            _save_episodes(repo_root, episodes)
            return f"Episode {episode_id} closed: {ep['title']}"
    return f"Episode {episode_id} not found."


def format_episode(repo_root: Path, episode_id: str = "") -> str:
    """Format an episode as a readable story."""
    episodes = _load_episodes(repo_root)
    if not episodes:
        return "No engineering episodes recorded."

    if episode_id:
        ep = next((e for e in episodes if e["id"] == episode_id), None)
        if not ep:
            return f"Episode {episode_id} not found."
        return _format_single(ep)

    # Show recent episodes
    lines = ["# Engineering Episodes\n"]
    for ep in episodes[-10:]:
        status = "✅" if ep.get("status") == "closed" else "🔄"
        lines.append(f"- {status} **{ep['id']}**: {ep['title']} ({len(ep.get('items', []))} items)")
    return "\n".join(lines)


def _format_single(ep: dict[str, Any]) -> str:
    """Format a single episode as a narrative."""
    lines = [f"# Episode {ep['id']}: {ep['title']}\n"]
    if ep.get("problem"):
        lines.append(f"**Problem:** {ep['problem']}\n")

    if ep.get("items"):
        lines.append("## Timeline")
        for item in ep["items"]:
            lines.append(f"- [{item['type']}] {item['content']}")

    if ep.get("outcome"):
        lines.append(f"\n**Outcome:** {ep['outcome']}")

    return "\n".join(lines)
