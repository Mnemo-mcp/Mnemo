"""Plan Mode tools."""

from __future__ import annotations

from pathlib import Path

from ..tool_registry import tool, register


@tool("mnemo_plan",
      "Plan mode — create, track, and update task plans. Actions: create (new plan), done (mark task complete), add (add task to plan), remove (remove task), status (show progress), task (set/get current task), task_done (mark task complete).",
      properties={
          "action": {"type": "string", "description": "create, done, add, remove, status, task, or task_done"},
          "title": {"type": "string", "description": "Plan title (for create) or task title (for add)"},
          "tasks": {"type": "array", "items": {"type": "string"}, "description": "List of task descriptions (for create)"},
          "task_id": {"type": "string", "description": "Task ID like MNO-801 (for done/remove) or ticket ID (for task/task_done)"},
          "summary": {"type": "string", "description": "Completion summary (for done/task_done)"},
          "plan": {"type": "string", "description": "Plan title to add task to (for add)"},
          "priority": {"type": "string", "description": "high, medium, or low (for create)"},
          "description": {"type": "string", "description": "Task description (for task)"},
          "files": {"type": "array", "items": {"type": "string"}, "description": "Files involved (for task)"},
          "notes": {"type": "string", "description": "Notes (for task)"},
      },
      required=["action"])
def _plan(root: Path, args: dict) -> str:
    action = args.get("action", "status")

    if action == "task":
        return _handle_task(root, args)
    elif action == "task_done":
        return _handle_task_done(root, args)

    from ..plan import handle_plan
    return handle_plan(root, args)


def _handle_task(root: Path, args: dict) -> str:
    from ..sprint import set_current_task, get_current_task
    task_id = args.get("task_id", "")
    if not task_id:
        return get_current_task(root)
    set_current_task(root, task_id, args.get("description", ""),
                     args.get("files", []), args.get("notes", ""))
    return f"Task {task_id} set as active."


def _handle_task_done(root: Path, args: dict) -> str:
    from ..sprint import complete_task, _load_tasks
    from ..storage import Collections, get_storage
    from ..memory import add_memory

    task_id = args.get("task_id", "")
    if not task_id:
        return "Provide a task_id."
    summary = args.get("summary", "")
    result = complete_task(root, task_id, summary)
    try:
        tasks = _load_tasks(root)
        task_entry = next((t for t in tasks if t.get("task_id") == task_id), None)
        if task_entry:
            desc = task_entry.get("description", task_id)
            files = task_entry.get("files", [])
            storage = get_storage(root)
            memories = storage.read_collection(Collections.MEMORY)
            if not isinstance(memories, list):
                memories = []
            decisions = [m for m in memories[-10:] if m.get("category") == "decision"]
            decision_text = "; ".join(d.get("content", "")[:50] for d in decisions[:3])
            crystal = f"Completed [{desc}]: {summary or 'done'}. Files: {', '.join(files[:5]) or 'none'}."
            if decision_text:
                crystal += f" Decisions: {decision_text}"
            add_memory(root, crystal, "pattern", source="crystal")
            errors = [m for m in memories[-10:] if m.get("category") == "bug"]
            for err in errors[:2]:
                lesson = f"Lesson from {task_id}: {err.get('content', '')[:100]}"
                add_memory(root, lesson, "pattern", source="lesson")
    except Exception as exc:
        from ..utils.logger import get_logger
        get_logger("tools.plan").debug(f"Crystallization failed: {exc}")
    return result


# Register old tool names as aliases pointing to the same handler
def _task_alias(root: Path, args: dict) -> str:
    """Alias for mnemo_task -> mnemo_plan action=task."""
    args = dict(args)
    args["action"] = "task"
    return _plan(root, args)


def _task_done_alias(root: Path, args: dict) -> str:
    """Alias for mnemo_task_done -> mnemo_plan action=task_done."""
    args = dict(args)
    args["action"] = "task_done"
    return _plan(root, args)


register("mnemo_task", _task_alias, {
    "description": "Set or get the current task/ticket being worked on. Without task_id, shows active tasks.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Path to the repository root (auto-detected if omitted)"},
            "task_id": {"type": "string", "description": "Ticket ID (e.g. JIRA-123)"},
            "description": {"type": "string"},
            "files": {"type": "array", "items": {"type": "string"}},
            "notes": {"type": "string"},
        },
    },
})

register("mnemo_task_done", _task_done_alias, {
    "description": "Mark a task as completed.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Path to the repository root (auto-detected if omitted)"},
            "task_id": {"type": "string"},
            "summary": {"type": "string"},
        },
        "required": ["task_id"],
    },
})
