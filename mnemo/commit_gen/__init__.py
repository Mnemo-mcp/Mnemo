"""Commit message generator - reads git diff + memory to produce structured commit messages."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ..storage import Collections, get_storage


def _git_diff_staged(repo_root: Path) -> str:
    """Get staged diff, fall back to unstaged if nothing staged."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--stat"],
            cwd=repo_root, capture_output=True, text=True, timeout=10,
        )
        if result.stdout.strip():
            diff = subprocess.run(
                ["git", "diff", "--cached"],
                cwd=repo_root, capture_output=True, text=True, timeout=10,
            )
            return diff.stdout[:8000]

        # Nothing staged — use unstaged
        diff = subprocess.run(
            ["git", "diff"],
            cwd=repo_root, capture_output=True, text=True, timeout=10,
        )
        return diff.stdout[:8000]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def _git_diff_stat(repo_root: Path) -> str:
    """Get a compact stat summary of changes."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--stat"],
            cwd=repo_root, capture_output=True, text=True, timeout=10,
        )
        if result.stdout.strip():
            return result.stdout.strip()
        result = subprocess.run(
            ["git", "diff", "--stat"],
            cwd=repo_root, capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def _recent_memory(repo_root: Path, limit: int = 5) -> list[str]:
    """Get recent memory entries for context."""
    storage = get_storage(repo_root)
    entries = storage.read_collection(Collections.MEMORY)
    if not isinstance(entries, list):
        return []
    return [e.get("content", "") for e in entries[-limit:]]


def _classify_change(diff: str, stat: str) -> str:
    """Infer conventional commit type from diff content."""
    diff_lower = diff.lower()
    stat_lower = stat.lower()

    if "test" in stat_lower:
        if all("test" in line.lower() for line in stat.splitlines() if "|" in line):
            return "test"
    if any(f in stat_lower for f in ("readme", "docs/", ".md")):
        if all(any(d in line.lower() for d in ("readme", "docs/", ".md")) for line in stat.splitlines() if "|" in line):
            return "docs"
    if any(f in stat_lower for f in ("ci/", ".github/", "workflow")):
        return "ci"
    if any(k in diff_lower for k in ("fix", "bug", "error", "crash", "patch")):
        return "fix"
    if any(k in diff_lower for k in ("add", "new", "implement", "feature")):
        return "feat"
    if any(k in diff_lower for k in ("refactor", "rename", "move", "restructure")):
        return "refactor"
    return "feat"


def _extract_scope(stat: str) -> str:
    """Infer scope from changed file paths."""
    lines = [l for l in stat.splitlines() if "|" in l]
    if not lines:
        return ""
    paths = [l.split("|")[0].strip() for l in lines]
    # Find common directory
    parts_list = [p.split("/") for p in paths if "/" in p]
    if not parts_list:
        return ""
    if len(parts_list) == 1:
        return parts_list[0][-2] if len(parts_list[0]) > 1 else ""
    # Common prefix
    common = parts_list[0]
    for parts in parts_list[1:]:
        common = [a for a, b in zip(common, parts) if a == b]
        if not common:
            break
    return common[-1] if common else parts_list[0][0]


def generate_commit_message(repo_root: Path) -> str:
    """Generate a commit message from git diff and recent memory."""
    diff = _git_diff_staged(repo_root)
    stat = _git_diff_stat(repo_root)

    if not diff and not stat:
        return "No changes detected. Stage files with `git add` first."

    commit_type = _classify_change(diff, stat)
    scope = _extract_scope(stat)
    memory = _recent_memory(repo_root)

    # Build the message
    scope_str = f"({scope})" if scope else ""
    lines = stat.splitlines()
    file_count = len([l for l in lines if "|" in l])

    # Summary line
    # Extract what actually changed from the diff
    added_funcs = []
    removed_funcs = []
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            if "def " in line or "function " in line or "class " in line:
                added_funcs.append(line.strip().lstrip("+").strip())
        elif line.startswith("-") and not line.startswith("---"):
            if "def " in line or "function " in line or "class " in line:
                removed_funcs.append(line.strip().lstrip("-").strip())

    # Build description
    if added_funcs and not removed_funcs:
        subject = f"add {added_funcs[0].split('(')[0].replace('def ', '').replace('function ', '').strip()}"
        if len(added_funcs) > 1:
            subject += f" and {len(added_funcs) - 1} more"
    elif removed_funcs and not added_funcs:
        subject = f"remove {removed_funcs[0].split('(')[0].replace('def ', '').replace('function ', '').strip()}"
    elif file_count == 1:
        filename = lines[0].split("|")[0].strip().split("/")[-1] if lines else "file"
        subject = f"update {filename}"
    else:
        subject = f"update {file_count} files"

    header = f"{commit_type}{scope_str}: {subject}"

    # Body
    body_parts = []
    if stat:
        body_parts.append(f"Changes:\n{stat}")

    # Include relevant memory context
    if memory:
        relevant = [m for m in memory if any(
            word in m.lower() for word in subject.lower().split() if len(word) > 3
        )]
        if relevant:
            body_parts.append("Context from memory:\n" + "\n".join(f"- {m}" for m in relevant[:3]))

    body = "\n\n".join(body_parts)
    return f"{header}\n\n{body}" if body else header
