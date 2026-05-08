"""Sprint/Task Context — store and recall task-specific context."""

from __future__ import annotations

import json
import time
from pathlib import Path

from ..config import mnemo_path

TASKS_FILE = "tasks.json"


def _tasks_path(repo_root: Path) -> Path:
    return mnemo_path(repo_root) / TASKS_FILE


def _load_tasks(repo_root: Path) -> list[dict]:
    path = _tasks_path(repo_root)
    if path.exists():
        return json.loads(path.read_text())
    return []


def _save_tasks(repo_root: Path, tasks: list[dict]):
    _tasks_path(repo_root).write_text(json.dumps(tasks, indent=2))


def set_current_task(repo_root: Path, task_id: str, description: str = "",
                     files: list[str] = None, notes: str = "") -> dict:
    """Set the current task/ticket being worked on."""
    tasks = _load_tasks(repo_root)

    # Check if task already exists
    for t in tasks:
        if t["task_id"] == task_id:
            t["last_active"] = time.time()
            if description:
                t["description"] = description
            if files:
                t["files"] = list(set(t.get("files", []) + files))
            if notes:
                t["notes"] = t.get("notes", "") + "\n" + notes
            t["status"] = "active"
            _save_tasks(repo_root, tasks)
            return t

    # New task
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
    for t in tasks:
        if t["task_id"] == task_id:
            t["status"] = "completed"
            t["completed_at"] = time.time()
            if summary:
                t["summary"] = summary
            _save_tasks(repo_root, tasks)
            return f"Task {task_id} marked complete."
    return f"Task {task_id} not found."


def get_current_task(repo_root: Path) -> str:
    """Get the currently active task context."""
    tasks = _load_tasks(repo_root)
    active = [t for t in tasks if t.get("status") == "active"]

    if not active:
        return "No active task. Use mnemo_task to set one."

    lines = ["# Active Tasks\n"]
    for t in active:
        lines.append(f"## {t['task_id']}")
        if t.get("description"):
            lines.append(t["description"])
        if t.get("files"):
            lines.append(f"**Files:** {', '.join(t['files'])}")
        if t.get("notes"):
            lines.append(f"**Notes:** {t['notes']}")
        lines.append("")
    return "\n".join(lines)


def format_tasks(repo_root: Path) -> str:
    """Format all tasks as markdown."""
    tasks = _load_tasks(repo_root)
    if not tasks:
        return "No tasks stored."

    lines = ["# Task History\n"]
    for t in tasks[-20:]:
        status = "✓" if t.get("status") == "completed" else "→"
        lines.append(f"- {status} **{t['task_id']}** — {t.get('description', '')[:80]}")
    return "\n".join(lines)
