"""Plan mode — create, track, and auto-update task plans."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from ..config import mnemo_path


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


def create_plan(repo_root: Path, title: str, tasks: list[str], priority: str = "high", draft: bool = False) -> str:
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
            "priority": 3,
        })

    plan = {
        "title": title,
        "priority": priority,
        "created": time.time(),
        "status": "draft" if draft else "active",
        "draft": draft,
        "expires_at": time.time() + 86400 if draft else None,
        "tasks": plan_tasks,
    }
    plans.append(plan)
    _save_plans(repo_root, plans)
    _sync_tasks_md(repo_root, plans)

    prefix = "📝 Draft " if draft else ""
    lines = [f"# {prefix}Plan Created: {title}\n"]
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
                result = f"✅ `{task_id}` marked done: {task['title']}" + (f"\n  Summary: {summary}" if summary else "")
                # Check if this unblocks other tasks
                unblocked = []
                done_ids = {t["id"] for p in plans for t in p.get("tasks", []) if t["status"] == "done"}
                for p in plans:
                    for t in p.get("tasks", []):
                        if t["status"] != "open":
                            continue
                        requires = t.get("requires", [])
                        if task_id in requires and all(r in done_ids for r in requires):
                            unblocked.append(t)
                if unblocked:
                    result += "\n🔓 Unblocked: " + ", ".join(f"`{t['id']}` {t['title']}" for t in unblocked)
                return result
    return f"Task `{task_id}` not found."


def add_dependency(repo_root: Path, task_id: str, requires_id: str) -> str:
    """Add a dependency: task_id requires requires_id to be done first."""
    plans = _load_plans(repo_root)
    task_found = False
    requires_found = False
    for plan in plans:
        for task in plan.get("tasks", []):
            if task["id"] == task_id:
                task_found = True
                if "requires" not in task:
                    task["requires"] = []
                if requires_id not in task["requires"]:
                    task["requires"].append(requires_id)
                if "unlocks" not in task:
                    task["unlocks"] = []
            if task["id"] == requires_id:
                requires_found = True
                if "unlocks" not in task:
                    task["unlocks"] = []
                if task_id not in task["unlocks"]:
                    task["unlocks"].append(task_id)
    if not task_found:
        return f"Task `{task_id}` not found."
    if not requires_found:
        return f"Task `{requires_id}` not found."
    _save_plans(repo_root, plans)
    return f"✅ `{task_id}` now requires `{requires_id}`"


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

    # Auto-GC expired drafts
    now = time.time()
    plans = [p for p in plans if not (p.get("draft") and p.get("expires_at") and p["expires_at"] < now)]
    _save_plans(repo_root, plans)

    if not plans:
        return "No active plans."

    lines = ["# Plan Status\n"]
    for plan in plans:
        total = len(plan["tasks"])
        done = sum(1 for t in plan["tasks"] if t["status"] == "done")
        done_ids = {t["id"] for t in plan["tasks"] if t["status"] == "done"}
        if plan.get("draft"):
            status_icon = "📝"
            prefix = "Draft: "
        elif plan["status"] == "completed":
            status_icon = "✅"
            prefix = ""
        else:
            status_icon = "🔲"
            prefix = ""
        lines.append(f"## {status_icon} {prefix}{plan['title']} ({done}/{total})\n")
        for task in plan["tasks"]:
            requires = task.get("requires", [])
            is_blocked = task["status"] == "open" and requires and not all(r in done_ids for r in requires)
            if task["status"] == "done":
                check = "x"
            elif is_blocked:
                check = "🚫"
            else:
                check = " "
            lines.append(f"- [{check}] `{task['id']}` {task['title']}")
            if is_blocked:
                lines.append(f"  - Blocked by: {', '.join(r for r in requires if r not in done_ids)}")
            if task.get("summary"):
                lines.append(f"  - Done: {task['summary']}")
        lines.append("")

    # Show next action using frontier scoring
    next_task = _get_next_task(plans, now)
    if next_task:
        lines.append(f"**Next:** `{next_task['id']}` — {next_task['title']}")

    return "\n".join(lines)


def _get_next_task(plans: list[dict], now: float) -> dict | None:
    """Get highest-scored incomplete task across active plans (frontier scoring), skipping blocked."""
    # Build set of done task IDs
    done_ids = set()
    for plan in plans:
        for task in plan.get("tasks", []):
            if task["status"] == "done":
                done_ids.add(task["id"])

    candidates = []
    for plan in plans:
        if plan["status"] != "active":
            continue
        for task in plan["tasks"]:
            if task["status"] != "open":
                continue
            # Skip blocked tasks
            requires = task.get("requires", [])
            if requires and not all(r in done_ids for r in requires):
                continue
            priority = task.get("priority", 3)
            days_waiting = (now - task.get("created", now)) / 86400
            score = priority * 10 + days_waiting * 0.5
            candidates.append((score, task))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def get_active_plan_hint(repo_root: Path) -> str | None:
    """Get a one-line hint about the active plan's next task. Returns None if no active plan."""
    plans = _load_plans(repo_root)
    now = time.time()
    # Filter expired drafts
    plans = [p for p in plans if not (p.get("draft") and p.get("expires_at") and p["expires_at"] < now)]
    next_task = _get_next_task(plans, now)
    if not next_task:
        return None
    # Find which plan it belongs to
    for plan in plans:
        if plan["status"] != "active":
            continue
        total = len(plan["tasks"])
        done = sum(1 for t in plan["tasks"] if t["status"] == "done")
        if any(t["id"] == next_task["id"] for t in plan["tasks"]):
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
    """Sync plans to .mnemo/TASKS.md."""
    from ..config import mnemo_path
    tasks_md = mnemo_path(repo_root) / "TASKS.md"

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


def save_template(repo_root: Path, plan_id: str, name: str) -> str:
    """Save a plan's structure as a reusable template."""
    plans = _load_plans(repo_root)
    plan = None
    for p in plans:
        if plan_id.lower() in p.get("title", "").lower():
            plan = p
            break
        for t in p.get("tasks", []):
            if t.get("id") == plan_id:
                plan = p
                break
        if plan:
            break
    if not plan:
        return f"No plan matching '{plan_id}' found."

    templates_path = mnemo_path(repo_root) / "templates.json"
    templates = []
    if templates_path.exists():
        try:
            templates = json.loads(templates_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            templates = []

    template = {
        "name": name,
        "title_pattern": plan["title"],
        "priority": plan.get("priority", "high"),
        "tasks": [t["title"] for t in plan.get("tasks", [])],
        "created": time.time(),
    }
    # Replace existing template with same name
    templates = [t for t in templates if t.get("name") != name]
    templates.append(template)
    templates_path.write_text(json.dumps(templates, indent=2) + "\n", encoding="utf-8")
    return f"Template '{name}' saved with {len(template['tasks'])} tasks."


def from_template(repo_root: Path, name: str) -> str:
    """Create a new plan from a saved template."""
    templates_path = mnemo_path(repo_root) / "templates.json"
    if not templates_path.exists():
        return "No templates found."
    try:
        templates = json.loads(templates_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "Failed to read templates."

    template = next((t for t in templates if t.get("name") == name), None)
    if not template:
        available = ", ".join(t.get("name", "") for t in templates)
        return f"Template '{name}' not found. Available: {available}"

    return create_plan(repo_root, template["title_pattern"], template["tasks"], template.get("priority", "high"))


def handle_plan(repo_root: Path, arguments: dict) -> str:
    """MCP tool handler for mnemo_plan."""
    action = arguments.get("action", "status")

    if action == "create":
        title = arguments.get("title", "")
        tasks = arguments.get("tasks", [])
        if isinstance(tasks, str):
            tasks = [t.strip() for t in tasks.split(",") if t.strip()]
        if not title:
            return "Provide a plan title."
        if not tasks:
            return "Provide at least one task."
        priority = arguments.get("priority", "high")
        draft = arguments.get("draft", False)
        return create_plan(repo_root, title, tasks, priority, draft=draft)

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

    elif action == "promote":
        return _promote_plan(repo_root, arguments.get("title", ""))

    elif action == "depends":
        task_id = arguments.get("task_id", "")
        requires_id = arguments.get("requires", "")
        if not task_id or not requires_id:
            return "Provide both 'task_id' and 'requires'."
        return add_dependency(repo_root, task_id, requires_id)

    elif action == "save-template":
        plan_id = arguments.get("plan_id", arguments.get("plan", ""))
        name = arguments.get("name", "")
        if not plan_id or not name:
            return "Provide 'plan_id' (or 'plan') and 'name' for the template."
        return save_template(repo_root, plan_id, name)

    elif action == "from-template":
        name = arguments.get("name", "")
        if not name:
            return "Provide template 'name'."
        return from_template(repo_root, name)

    elif action == "status":
        return get_status(repo_root)

    return f"Unknown action: {action}. Use: create, done, add, remove, depends, promote, save-template, from-template, status"


def _promote_plan(repo_root: Path, title: str) -> str:
    """Promote a draft plan to active."""
    plans = _load_plans(repo_root)
    for plan in plans:
        if title.lower() in plan.get("title", "").lower() and plan.get("draft"):
            plan["draft"] = False
            plan["expires_at"] = None
            plan["status"] = "active"
            _save_plans(repo_root, plans)
            return f"✅ Plan '{plan['title']}' promoted from draft to active."
    return f"No draft plan matching '{title}' found."


# --- Auto-plan detection ---

_PLAN_SIGNALS = re.compile(
    r'\b(plan|migrate|migration|refactor|implement|add support|convert|replace|upgrade|move to|switch to|introduce|build|create|set up)\b',
    re.I,
)

_TASK_VERBS = re.compile(
    r'^\s*[-\*\d]+[.)\s]+(add|create|update|remove|fix|implement|migrate|convert|refactor|replace|build|set up|configure|deploy|test|write|move|split|merge|extract)\b',
    re.I | re.M,
)

_STEP_PATTERNS = [
    re.compile(r'^\s*[-\*\d]+[.)\s]', re.M),  # bullet points or numbered lists
    re.compile(r'\b(step \d|phase \d|first|then|next|finally|after that)\b', re.I),
]


def _looks_like_plan(text: str) -> bool:
    """Detect if text describes work that should be tracked as a plan.
    
    Requires BOTH a plan-level signal AND actionable bullet items.
    Simple lists of facts/observations won't trigger this.
    """
    # Must have a high-level action signal
    if not _PLAN_SIGNALS.search(text):
        return False

    # Must have 3+ bullet points that START with action verbs
    actionable_bullets = _TASK_VERBS.findall(text)
    if len(actionable_bullets) >= 3:
        return True

    # Or 4+ plain bullets WITH sequential language
    bullet_count = len(re.findall(r'^\s*[-\*\d]+[.)\s]', text, re.M))
    if bullet_count >= 4:
        for pattern in _STEP_PATTERNS[1:]:  # sequential language patterns
            if len(pattern.findall(text)) >= 2:
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
    """If text looks like a deliberate plan (not just context), auto-create it.
    
    Only triggers when text has BOTH:
    - Action verbs indicating work to be done (migrate, implement, refactor, etc.)
    - 3+ concrete task-like items (bullet points with actionable language)
    
    Does NOT trigger on:
    - General context/notes being remembered
    - Lists of facts or observations
    - Single-line memories even with action verbs
    """
    if not _looks_like_plan(text):
        return None

    tasks = _extract_tasks_from_text(text)
    if len(tasks) < 3:  # Require at least 3 tasks (was 2 - too easy to trigger)
        return None

    title = _extract_plan_title(text)
    result = create_plan(repo_root, title, tasks, priority="high")
    return f"📋 Auto-created plan from {source}:\n{result}"
