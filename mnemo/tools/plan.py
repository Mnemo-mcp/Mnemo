"""Plan Mode tools."""

from __future__ import annotations

from pathlib import Path

from ..tool_registry import tool


@tool("mnemo_plan",
      "Plan mode — create, track, and update task plans. Actions: create (new plan), done (mark task complete), add (add task to plan), remove (remove task), status (show progress). Plans auto-sync to TASKS.md.",
      properties={
          "action": {"type": "string", "description": "create, done, add, remove, or status"},
          "title": {"type": "string", "description": "Plan title (for create) or task title (for add)"},
          "tasks": {"type": "array", "items": {"type": "string"}, "description": "List of task descriptions (for create)"},
          "task_id": {"type": "string", "description": "Task ID like MNO-801 (for done/remove)"},
          "summary": {"type": "string", "description": "Completion summary (for done)"},
          "plan": {"type": "string", "description": "Plan title to add task to (for add)"},
          "priority": {"type": "string", "description": "high, medium, or low (for create)"},
      },
      required=["action"])
def _plan(root: Path, args: dict) -> str:
    from ..plan import handle_plan
    return handle_plan(root, args)
