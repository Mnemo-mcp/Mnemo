"""Sprint/task context - store and recall task-specific context."""

from __future__ import annotations

import time
from pathlib import Path

from ..storage import Collections, get_storage


def _load_tasks(repo_root: Path) -> list[dict]:
    data = get_storage(repo_root).read_collection(Collections.TASKS)
    return data if isinstance(data, list) else []


def _save_tasks(repo_root: Path, tasks: list[dict]) -> None:
    get_storage(repo_root).write_collection(Collections.TASKS, tasks)


def set_current_task(
    repo_root: Path,
    task_id: str,
    description: str = "",
    files: list[str] | None = None,
    notes: str = "",
) -> dict:
    """Set the current task/ticket being worked on."""
    tasks = _load_tasks(repo_root)

    for task in tasks:
        if task["task_id"] == task_id:
            task["last_active"] = time.time()
            if description:
                task["description"] = description
            if files:
                task["files"] = sorted(set(task.get("files", []) + files))
            if notes:
                task["notes"] = task.get("notes", "") + "\n" + notes
            task["status"] = "active"
            _save_tasks(repo_root, tasks)
            return task

    entry = {
        "task_id": task_id,
        "description": description,
        "files": files or [],
        "notes": notes,
        "status": "active",
        "created": time.time(),
        "last_active": time.time(),
    }
    tasks.append(entry)
    _save_tasks(repo_root, tasks)
    return entry


def complete_task(repo_root: Path, task_id: str, summary: str = "") -> str:
    """Mark a task as complete with an optional summary."""
    tasks = _load_tasks(repo_root)
    for task in tasks:
        if task["task_id"] == task_id:
            task["status"] = "completed"
            task["completed_at"] = time.time()
            if summary:
                task["summary"] = summary
            _save_tasks(repo_root, tasks)
            return f"Task {task_id} marked complete."
    return f"Task {task_id} not found."


def get_current_task(repo_root: Path) -> str:
    """Get the currently active task context."""
    tasks = _load_tasks(repo_root)
    active = [task for task in tasks if task.get("status") == "active"]

    if not active:
        return "No active task. Use mnemo_task to set one."

    lines = ["# Active Tasks\n"]
    for task in active:
        lines.append(f"## {task['task_id']}")
        if task.get("description"):
            lines.append(task["description"])
        if task.get("files"):
            lines.append(f"**Files:** {', '.join(task['files'])}")
        if task.get("notes"):
            lines.append(f"**Notes:** {task['notes']}")
        lines.append("")
    return "\n".join(lines)


def format_tasks(repo_root: Path) -> str:
    """Format all tasks as markdown."""
    tasks = _load_tasks(repo_root)
    if not tasks:
        return "No tasks stored."

    lines = ["# Task History\n"]
    for task in tasks[-20:]:
        status = "done" if task.get("status") == "completed" else "active"
        lines.append(f"- {status}: **{task['task_id']}** - {task.get('description', '')[:80]}")
    return "\n".join(lines)
