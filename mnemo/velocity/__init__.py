"""Velocity tracking - parse git log for development metrics."""

from __future__ import annotations

import subprocess
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


def _git_log(repo_root: Path, days: int = 30) -> list[dict]:
    """Parse git log for the last N days."""
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        result = subprocess.run(
            ["git", "log", f"--since={since}", "--format=%H|%ai|%an|%s", "--no-merges"],
            cwd=repo_root, capture_output=True, text=True, timeout=15,
        )
        if not result.stdout.strip():
            return []
        entries = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("|", 3)
            if len(parts) == 4:
                entries.append({
                    "hash": parts[0],
                    "date": parts[1].split()[0],
                    "author": parts[2],
                    "message": parts[3],
                })
        return entries
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def _git_shortstat(repo_root: Path, days: int = 7) -> dict:
    """Get insertions/deletions for the period."""
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        result = subprocess.run(
            ["git", "log", f"--since={since}", "--shortstat", "--no-merges", "--format="],
            cwd=repo_root, capture_output=True, text=True, timeout=15,
        )
        insertions = 0
        deletions = 0
        for line in result.stdout.splitlines():
            if "insertion" in line:
                parts = line.split(",")
                for p in parts:
                    if "insertion" in p:
                        insertions += int(p.strip().split()[0])
                    elif "deletion" in p:
                        deletions += int(p.strip().split()[0])
        return {"insertions": insertions, "deletions": deletions}
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {"insertions": 0, "deletions": 0}


def calculate_velocity(repo_root: Path) -> str:
    """Calculate development velocity metrics."""
    log_30d = _git_log(repo_root, days=30)
    log_7d = [e for e in log_30d if (datetime.now() - datetime.strptime(e["date"], "%Y-%m-%d")).days <= 7]
    stats_7d = _git_shortstat(repo_root, days=7)

    if not log_30d:
        return "No git history found in the last 30 days."

    # Commits per day
    by_date: dict[str, int] = defaultdict(int)
    for entry in log_30d:
        by_date[entry["date"]] += 1

    active_days = len(by_date)
    total_commits = len(log_30d)
    avg_per_day = total_commits / max(active_days, 1)

    # By author
    by_author: dict[str, int] = defaultdict(int)
    for entry in log_30d:
        by_author[entry["author"]] += 1

    lines = ["# Development Velocity\n"]
    lines.append("## Last 7 Days\n")
    lines.append(f"- Commits: **{len(log_7d)}**")
    lines.append(f"- Lines added: **{stats_7d['insertions']}**")
    lines.append(f"- Lines removed: **{stats_7d['deletions']}**")
    lines.append(f"- Net change: **{stats_7d['insertions'] - stats_7d['deletions']:+d}**")

    lines.append("\n## Last 30 Days\n")
    lines.append(f"- Total commits: **{total_commits}**")
    lines.append(f"- Active days: **{active_days}**")
    lines.append(f"- Avg commits/active day: **{avg_per_day:.1f}**")

    if len(by_author) > 1:
        lines.append("\n## By Author\n")
        for author, count in sorted(by_author.items(), key=lambda x: -x[1]):
            lines.append(f"- {author}: {count} commits")

    # Recent activity
    lines.append("\n## Recent Commits\n")
    for entry in log_30d[:10]:
        lines.append(f"- `{entry['date']}` {entry['message'][:60]}")

    return "\n".join(lines)
