"""PR description generator - reads diff from branch point + task context + memory."""

from __future__ import annotations

import subprocess  # nosec B404
from pathlib import Path

from ..storage import Collections, get_storage


def _git_main_branch(repo_root: Path) -> str:
    """Detect the main branch name."""
    for name in ("main", "master", "develop"):
        result = subprocess.run(  # nosec B603 B607
            ["git", "rev-parse", "--verify", name],
            cwd=repo_root, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return name
    return "main"


def _git_branch_diff(repo_root: Path) -> tuple[str, str, str]:
    """Get diff stat, file list, and full diff from branch point."""
    try:
        base = _git_main_branch(repo_root)
        # Merge base
        merge_base = subprocess.run(  # nosec B603 B607
            ["git", "merge-base", base, "HEAD"],
            cwd=repo_root, capture_output=True, text=True, timeout=5,
        )
        ref = merge_base.stdout.strip() if merge_base.returncode == 0 else base

        stat = subprocess.run(  # nosec B603 B607
            ["git", "diff", "--stat", ref],
            cwd=repo_root, capture_output=True, text=True, timeout=10,
        )
        diff = subprocess.run(  # nosec B603 B607
            ["git", "diff", ref],
            cwd=repo_root, capture_output=True, text=True, timeout=10,
        )
        log = subprocess.run(  # nosec B603 B607
            ["git", "log", "--oneline", f"{ref}..HEAD"],
            cwd=repo_root, capture_output=True, text=True, timeout=10,
        )
        return stat.stdout.strip(), diff.stdout[:10000], log.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "", "", ""


def _current_branch(repo_root: Path) -> str:
    """Get current branch name."""
    try:
        result = subprocess.run(  # nosec B603 B607
            ["git", "branch", "--show-current"],
            cwd=repo_root, capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def _active_task(repo_root: Path) -> dict | None:
    """Get the active task if any."""
    storage = get_storage(repo_root)
    tasks = storage.read_collection(Collections.TASKS)
    if not isinstance(tasks, list):
        return None
    active = [t for t in tasks if t.get("status") == "active"]
    return active[-1] if active else None


def _recent_memory(repo_root: Path, limit: int = 5) -> list[str]:
    """Get recent memory entries."""
    storage = get_storage(repo_root)
    entries = storage.read_collection(Collections.MEMORY)
    if not isinstance(entries, list):
        return []
    return [e.get("content", "") for e in entries[-limit:]]


def generate_pr_description(repo_root: Path) -> str:
    """Generate a PR description from branch diff, task context, and memory."""
    stat, diff, commits = _git_branch_diff(repo_root)
    branch = _current_branch(repo_root)
    task = _active_task(repo_root)

    if not stat and not diff:
        return "No changes found compared to base branch."

    sections = []

    # Title
    if task:
        title = f"{task.get('task_id', '')}: {task.get('description', branch)}"
    elif branch:
        title = branch.replace("-", " ").replace("/", ": ")
    else:
        title = "Changes"
    sections.append(f"## {title}\n")

    # Summary
    sections.append("### Summary\n")
    if task and task.get("description"):
        sections.append(task["description"])
    if task and task.get("notes"):
        sections.append(f"\n{task['notes']}")
    sections.append("")

    # Changes
    sections.append("### Changes\n")
    if commits:
        for line in commits.splitlines()[:20]:
            sections.append(f"- {line.split(' ', 1)[-1] if ' ' in line else line}")
    sections.append("")

    # Files changed
    sections.append("### Files\n")
    sections.append(f"```\n{stat}\n```")

    # Context from memory
    memory = _recent_memory(repo_root)
    relevant = []
    if diff:
        diff_words = set(w.lower() for w in diff.split()[:500] if len(w) > 4)
        for m in memory:
            if any(word in m.lower() for word in list(diff_words)[:50]):
                relevant.append(m)
    if relevant:
        sections.append("\n### Context\n")
        for m in relevant[:3]:
            sections.append(f"- {m}")

    # Testing notes placeholder
    sections.append("\n### Testing\n")
    sections.append("- [ ] Unit tests pass")
    sections.append("- [ ] Manual verification")

    return "\n".join(sections)
