"""Code Health Score — track complexity hotspots, churn, and metrics."""

from __future__ import annotations

import re
from pathlib import Path

from ..config import IGNORE_DIRS


def _should_ignore(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)


def _count_methods(content: str) -> int:
    """Count methods in a C# file."""
    return len(re.findall(r'(public|private|protected|internal)\s+(static\s+)?(async\s+)?\S+\s+\w+\s*\(', content))


def _estimate_complexity(content: str) -> int:
    """Rough cyclomatic complexity estimate based on branching keywords."""
    keywords = ["if ", "else ", "switch ", "case ", "for ", "foreach ", "while ", "catch ", "&&", "||", "??", "?.", "=>"]
    return sum(content.count(k) for k in keywords)


def _get_git_churn(repo_root: Path, filepath: Path) -> int:
    """Get number of commits that touched this file."""
    try:
        from git import Repo
        repo = Repo(repo_root)
        rel = str(filepath.relative_to(repo_root))
        commits = list(repo.iter_commits(paths=rel, max_count=100))
        return len(commits)
    except Exception:
        return 0


def calculate_health(repo_root: Path) -> str:
    """Calculate code health metrics for the project."""
    lines = ["# Code Health Report\n"]

    hotspots: list[tuple[str, int, int, int]] = []  # (file, complexity, methods, lines)

    for cs_file in repo_root.rglob("*.cs"):
        if _should_ignore(cs_file) or "Test" in str(cs_file):
            continue
        try:
            content = cs_file.read_text(errors="replace")
        except (OSError, PermissionError):
            continue

        if len(content) < 100:
            continue

        rel = str(cs_file.relative_to(repo_root))
        complexity = _estimate_complexity(content)
        methods = _count_methods(content)
        line_count = content.count("\n")

        hotspots.append((rel, complexity, methods, line_count))

    if not hotspots:
        return "No source files found for health analysis."

    # Sort by complexity (highest first)
    hotspots.sort(key=lambda x: -x[1])

    # Overall stats
    total_files = len(hotspots)
    total_lines = sum(h[3] for h in hotspots)
    total_methods = sum(h[2] for h in hotspots)
    avg_complexity = sum(h[1] for h in hotspots) / total_files

    lines.append("## Summary")
    lines.append(f"- **Files:** {total_files}")
    lines.append(f"- **Total lines:** {total_lines:,}")
    lines.append(f"- **Total methods:** {total_methods}")
    lines.append(f"- **Avg complexity/file:** {avg_complexity:.1f}")
    lines.append("")

    # Complexity hotspots
    lines.append("## Complexity Hotspots (top 10)")
    lines.append("Files with highest branching complexity — candidates for refactoring:")
    lines.append("")
    for rel, complexity, methods, line_count in hotspots[:10]:
        lines.append(f"- **{rel}** — complexity: {complexity}, methods: {methods}, lines: {line_count}")
    lines.append("")

    # Large files
    large = sorted(hotspots, key=lambda x: -x[3])[:10]
    lines.append("## Largest Files (top 10)")
    for rel, complexity, methods, line_count in large:
        lines.append(f"- **{rel}** — {line_count} lines, {methods} methods")
    lines.append("")

    # Files with many methods (god classes)
    many_methods = sorted(hotspots, key=lambda x: -x[2])[:5]
    lines.append("## Potential God Classes (most methods)")
    for rel, complexity, methods, line_count in many_methods:
        if methods > 10:
            lines.append(f"- **{rel}** — {methods} methods")

    return "\n".join(lines)
