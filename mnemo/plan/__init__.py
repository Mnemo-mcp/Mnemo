"""Plan mode — create, track, and auto-update task plans."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from ..config import mnemo_path
from ..storage import get_storage


PLANS_FILE = "plans.json"


def _load_plans(repo_root: Path) -> list[dict[str, Any]]:
    path = mnemo_path(repo_root) / PLANS_FILE
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_plans(repo_root: Path, plans: list[dict[str, Any]]) -> None:
    path = mnemo_path(repo_root) / PLANS_FILE
    path.write_text(json.dumps(plans, indent=2) + "\n", encoding="utf-8")


def _next_id(plans: list[dict]) -> str:
    """Generate next MNO-XXX ID."""
    max_num = 0
    for plan in plans:
        for task in plan.get("tasks", []):
            match = re.match(r"MNO-(\d+)", task.get("id", ""))
            if match:
                max_num = max(max_num, int(match.group(1)))
    return f"MNO-{max_num + 1:03d}"


def _get_next_id_num(plans: list[dict]) -> int:
    max_num = 0
    for plan in plans:
        for task in plan.get("tasks", []):
            match = re.match(r"MNO-(\d+)", task.get("id", ""))
            if match:
                max_num = max(max_num, int(match.group(1)))
    return max_num + 1


def create_plan(repo_root: Path, title: str, tasks: list[str], priority: str = "high") -> str:
    """Create a new plan with tasks."""
    plans = _load_plans(repo_root)
    next_num = _get_next_id_num(plans)

    plan_tasks = []
    for i, task_title in enumerate(tasks):
        plan_tasks.append({
            "id": f"MNO-{next_num + i:03d}",
            "title": task_title,
            "status": "open",
            "created": time.time(),
            "completed": None,
            "summary": "",
        })

    plan = {
        "title": title,
        "priority": priority,
        "created": time.time(),
        "status": "active",
        "tasks": plan_tasks,
    }
    plans.append(plan)
    _save_plans(repo_root, plans)
    _sync_tasks_md(repo_root, plans)

    lines = [f"# Plan Created: {title}\n"]
    for t in plan_tasks:
        lines.append(f"- [ ] `{t['id']}` {t['title']}")
    return "\n".join(lines)


def mark_done(repo_root: Path, task_id: str, summary: str = "") -> str:
    """Mark a task as completed."""
    plans = _load_plans(repo_root)
    for plan in plans:
        for task in plan.get("tasks", []):
            if task["id"] == task_id:
                task["status"] = "done"
                task["completed"] = time.time()
                task["summary"] = summary
                # Check if all tasks done → mark plan complete
                if all(t["status"] == "done" for t in plan["tasks"]):
                    plan["status"] = "completed"
                _save_plans(repo_root, plans)
                _sync_tasks_md(repo_root, plans)
                return f"✅ `{task_id}` marked done: {task['title']}" + (f"\n  Summary: {summary}" if summary else "")
    return f"Task `{task_id}` not found."


def add_task(repo_root: Path, plan_title: str, task_title: str) -> str:
    """Add a task to an existing plan."""
    plans = _load_plans(repo_root)
    for plan in plans:
        if plan_title.lower() in plan["title"].lower():
            next_num = _get_next_id_num(plans)
            task = {
                "id": f"MNO-{next_num:03d}",
                "title": task_title,
                "status": "open",
                "created": time.time(),
                "completed": None,
                "summary": "",
            }
            plan["tasks"].append(task)
            _save_plans(repo_root, plans)
            _sync_tasks_md(repo_root, plans)
            return f"Added `{task['id']}` to plan '{plan['title']}': {task_title}"
    return f"No plan matching '{plan_title}' found."


def remove_task(repo_root: Path, task_id: str) -> str:
    """Remove a task from a plan."""
    plans = _load_plans(repo_root)
    for plan in plans:
        for i, task in enumerate(plan.get("tasks", [])):
            if task["id"] == task_id:
                removed = plan["tasks"].pop(i)
                _save_plans(repo_root, plans)
                _sync_tasks_md(repo_root, plans)
                return f"Removed `{task_id}`: {removed['title']}"
    return f"Task `{task_id}` not found."


def get_status(repo_root: Path) -> str:
    """Show current plan progress."""
    plans = _load_plans(repo_root)
    if not plans:
        return "No active plans."

    lines = ["# Plan Status\n"]
    for plan in plans:
        total = len(plan["tasks"])
        done = sum(1 for t in plan["tasks"] if t["status"] == "done")
        status_icon = "✅" if plan["status"] == "completed" else "🔲"
        lines.append(f"## {status_icon} {plan['title']} ({done}/{total})\n")
        for task in plan["tasks"]:
            check = "x" if task["status"] == "done" else " "
            lines.append(f"- [{check}] `{task['id']}` {task['title']}")
            if task.get("summary"):
                lines.append(f"  - Done: {task['summary']}")
        lines.append("")

    # Show next action
    for plan in plans:
        if plan["status"] == "active":
            next_task = next((t for t in plan["tasks"] if t["status"] == "open"), None)
            if next_task:
                lines.append(f"**Next:** `{next_task['id']}` — {next_task['title']}")
                break

    return "\n".join(lines)


def get_active_plan_hint(repo_root: Path) -> str | None:
    """Get a one-line hint about the active plan's next task. Returns None if no active plan."""
    plans = _load_plans(repo_root)
    for plan in plans:
        if plan["status"] != "active":
            continue
        total = len(plan["tasks"])
        done = sum(1 for t in plan["tasks"] if t["status"] == "done")
        next_task = next((t for t in plan["tasks"] if t["status"] == "open"), None)
        if next_task:
            return f"📋 Plan '{plan['title']}' ({done}/{total}) — next: `{next_task['id']}` {next_task['title']}"
    return None


def auto_detect_completion(repo_root: Path, text: str) -> str | None:
    """Check if text (from mnemo_remember or commit) matches an open plan task. Auto-marks done if so."""
    plans = _load_plans(repo_root)
    text_lower = text.lower()

    for plan in plans:
        for task in plan.get("tasks", []):
            if task["status"] != "open":
                continue
            # Match if task title keywords appear in the text
            title_words = set(task["title"].lower().split())
            # Need at least 60% of title words to match
            if len(title_words) < 3:
                continue
            matched = sum(1 for w in title_words if w in text_lower)
            if matched / len(title_words) >= 0.6:
                task["status"] = "done"
                task["completed"] = time.time()
                task["summary"] = f"Auto-detected from: {text[:100]}"
                if all(t["status"] == "done" for t in plan["tasks"]):
                    plan["status"] = "completed"
                _save_plans(repo_root, plans)
                _sync_tasks_md(repo_root, plans)
                return f"✅ Auto-completed `{task['id']}`: {task['title']}"
    return None


def _sync_tasks_md(repo_root: Path, plans: list[dict]) -> None:
    """Sync plans to TASKS.md — append/update the Active Plans section."""
    tasks_md = repo_root / "TASKS.md"

    # Build the active plans section
    section_lines = ["\n## Active Plans\n"]
    for plan in plans:
        total = len(plan["tasks"])
        done = sum(1 for t in plan["tasks"] if t["status"] == "done")
        status_icon = "✅" if plan["status"] == "completed" else "🔲"
        section_lines.append(f"### {status_icon} {plan['title']} ({done}/{total})\n")
        for task in plan["tasks"]:
            check = "x" if task["status"] == "done" else " "
            line = f"- [{check}] `{task['id']}` {task['title']}"
            if task.get("summary"):
                line += f"\n  - Done: {task['summary']}"
            section_lines.append(line)
        section_lines.append("")

    new_section = "\n".join(section_lines)

    if not tasks_md.exists():
        tasks_md.write_text(f"# Mnemo Task List\n{new_section}", encoding="utf-8")
        return

    content = tasks_md.read_text(encoding="utf-8")

    # Replace existing Active Plans section or append
    marker_start = "## Active Plans"
    if marker_start in content:
        # Find the section and replace it
        start_idx = content.index(marker_start)
        # Find next ## heading after this section
        rest = content[start_idx + len(marker_start):]
        next_heading = re.search(r'\n## [^A]', rest)  # Next ## that isn't "Active Plans" continuation
        if next_heading:
            end_idx = start_idx + len(marker_start) + next_heading.start()
            content = content[:start_idx] + new_section.strip() + "\n\n" + content[end_idx:]
        else:
            content = content[:start_idx] + new_section.strip() + "\n"
    else:
        content = content.rstrip() + "\n" + new_section

    tasks_md.write_text(content, encoding="utf-8")


def handle_plan(repo_root: Path, arguments: dict) -> str:
    """MCP tool handler for mnemo_plan."""
    action = arguments.get("action", "status")

    if action == "create":
        title = arguments.get("title", "")
        tasks = arguments.get("tasks", [])
        if not title:
            return "Provide a plan title."
        if not tasks:
            return "Provide at least one task."
        priority = arguments.get("priority", "high")
        return create_plan(repo_root, title, tasks, priority)

    elif action == "done":
        task_id = arguments.get("task_id", "")
        if not task_id:
            return "Provide a task_id to mark done."
        summary = arguments.get("summary", "")
        return mark_done(repo_root, task_id, summary)

    elif action == "add":
        plan_title = arguments.get("plan", "")
        task_title = arguments.get("title", "")
        if not plan_title or not task_title:
            return "Provide both 'plan' (plan title to add to) and 'title' (new task title)."
        return add_task(repo_root, plan_title, task_title)

    elif action == "remove":
        task_id = arguments.get("task_id", "")
        if not task_id:
            return "Provide a task_id to remove."
        return remove_task(repo_root, task_id)

    elif action == "status":
        return get_status(repo_root)

    return f"Unknown action: {action}. Use: create, done, add, remove, status"


# --- Auto-plan detection ---

_PLAN_SIGNALS = re.compile(
    r'\b(migrate|migration|refactor|implement|add support|convert|replace|upgrade|move to|switch to|introduce|build|create|set up)\b',
    re.I,
)

_STEP_PATTERNS = [
    re.compile(r'^\s*[-\*\d]+[.)\s]', re.M),  # bullet points or numbered lists
    re.compile(r'\b(step \d|phase \d|first|then|next|finally|after that)\b', re.I),
]


def _looks_like_plan(text: str) -> bool:
    """Detect if text describes work that should be tracked as a plan."""
    if not _PLAN_SIGNALS.search(text):
        return False
    # Must have multiple steps/items
    bullet_count = len(re.findall(r'^\s*[-\*\d]+[.)\s]', text, re.M))
    if bullet_count >= 3:
        return True
    # Or sequential language
    for pattern in _STEP_PATTERNS:
        if len(pattern.findall(text)) >= 2:
            return True
    # Or multiple services/components mentioned with action verbs
    if len(_PLAN_SIGNALS.findall(text)) >= 2:
        return True
    return False


def _extract_tasks_from_text(text: str) -> list[str]:
    """Extract task items from free-form text."""
    tasks = []

    # Try bullet points / numbered lists first
    bullets = re.findall(r'^\s*[-\*\d]+[.)\s]+(.+)$', text, re.M)
    if bullets:
        for b in bullets:
            b = b.strip().rstrip('.')
            if 10 < len(b) < 200:
                tasks.append(b)

    if tasks:
        return tasks

    # Try splitting by sentences that contain action verbs
    sentences = re.split(r'[.\n;]', text)
    for s in sentences:
        s = s.strip()
        if len(s) < 10 or len(s) > 200:
            continue
        if _PLAN_SIGNALS.search(s):
            tasks.append(s)

    return tasks


def _extract_plan_title(text: str) -> str:
    """Extract a short title from plan-like text."""
    first_line = text.strip().split('\n')[0].strip()
    first_line = re.sub(r'^[-\*\d]+[.)\s]+', '', first_line).strip()
    if len(first_line) > 80:
        first_line = first_line[:77] + "..."
    return first_line or "Untitled Plan"


def auto_create_plan_from_text(repo_root: Path, text: str, source: str = "memory") -> str | None:
    """If text looks like a plan, auto-create it. Returns message or None."""
    if not _looks_like_plan(text):
        return None

    tasks = _extract_tasks_from_text(text)
    if len(tasks) < 2:
        return None

    title = _extract_plan_title(text)
    result = create_plan(repo_root, title, tasks, priority="high")
    return f"📋 Auto-created plan from {source}:\n{result}"
