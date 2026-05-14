"""Observation & Meta tools."""

from __future__ import annotations

from pathlib import Path

from ..tool_registry import tool


@tool("mnemo_ask",
      "Intent-based meta-tool. Ask a natural language question and Mnemo routes to the right tools internally. Use for complex queries that span multiple tools.",
      properties={"query": {"type": "string", "description": "Natural language question (e.g. 'why does CosmosDbService exist?', 'what breaks if I change AuthService?')"}},
      required=["query"])
def _ask(root: Path, args: dict) -> str:
    from .meta import ask
    return ask(root, args.get("query", ""))


@tool("mnemo_episode",
      "Engineering episodes — track connected problem→decision→fix→outcome stories. Actions: list, start, close.",
      properties={
          "action": {"type": "string", "description": "list, start, or close"},
          "title": {"type": "string", "description": "Episode title (for start)"},
          "problem": {"type": "string", "description": "Problem description (for start)"},
          "episode_id": {"type": "string", "description": "Episode ID (for close or view)"},
          "outcome": {"type": "string", "description": "Outcome summary (for close)"},
      })
def _episode(root: Path, args: dict) -> str:
    from ..memory.episodes import format_episode, start_episode, close_episode
    action = args.get("action", "list")
    if action == "start":
        ep = start_episode(root, args.get("title", "Untitled"), args.get("problem", ""))
        return f"Started episode {ep['id']}: {ep['title']}"
    elif action == "close":
        return close_episode(root, args.get("episode_id", ""), args.get("outcome", ""))
    else:
        return format_episode(root, args.get("episode_id", ""))


@tool("mnemo_temporal",
      "Show temporal intelligence — file instability scores, change frequency, hotspots over time.")
def _temporal(root: Path, args: dict) -> str:
    from ..memory.temporal import format_temporal_report
    return format_temporal_report(root)
