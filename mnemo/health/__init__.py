"""Code Health Score — track complexity hotspots, churn, and metrics."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from ..config import IGNORE_DIRS, SUPPORTED_EXTENSIONS, should_ignore
from ..utils.logger import get_logger

logger = get_logger("health")


def _should_ignore(path: Path) -> bool:
    return should_ignore(path)


def _count_methods(content: str) -> int:
    """Count methods/functions in a source file (multi-language)."""
    # C#/Java style
    cs_methods = len(re.findall(r'(public|private|protected|internal)\s+(static\s+)?(async\s+)?\S+\s+\w+\s*\(', content))
    # Python style
    py_methods = len(re.findall(r'^\s*def\s+\w+\s*\(', content, re.MULTILINE))
    # JS/TS style
    js_methods = len(re.findall(r'(function\s+\w+\s*\(|\w+\s*\([^)]*\)\s*{|\w+\s*=\s*\([^)]*\)\s*=>)', content))
    # Go style
    go_methods = len(re.findall(r'^func\s+', content, re.MULTILINE))
    return max(cs_methods, py_methods, js_methods, go_methods)


def _estimate_complexity(content: str, language: str = "") -> int:
    """Rough cyclomatic complexity estimate based on branching keywords."""
    common = ["if ", "else ", "for ", "while ", "catch ", "&&", "||", "=>"]
    csharp_extra = ["switch ", "case ", "foreach ", "??", "?."]
    python_extra = ["elif ", "except ", "for ", "with "]
    js_extra = ["switch ", "case ", "? ", "catch "]

    keywords = list(common)
    if language in ("csharp",):
        keywords.extend(csharp_extra)
    elif language in ("python",):
        keywords.extend(python_extra)
    elif language in ("javascript", "typescript"):
        keywords.extend(js_extra)
    else:
        keywords.extend(csharp_extra)  # default broad set

    return sum(content.count(k) for k in keywords)


def _get_git_churn(repo_root: Path, filepath: Path) -> int:
    """Get number of commits that touched this file."""
    try:
        from git import Repo
        repo = Repo(repo_root)
        rel = str(filepath.relative_to(repo_root))
        commits = list(repo.iter_commits(paths=rel, max_count=100))
        return len(commits)
    except Exception as exc:
        logger.debug(f"Git churn lookup failed: {exc}")
        return 0


def system_health(repo_root: Path) -> dict:
    """Return system health metrics."""
    import resource
    import json

    mem_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)

    mnemo_dir = repo_root / ".mnemo"
    memories = 0
    decisions = 0
    graph_nodes = 0
    dir_size_kb = 0.0
    disk_breakdown: dict[str, float] = {}
    warnings: list[str] = []

    if mnemo_dir.exists():
        mem_file = mnemo_dir / "memory.json"
        if mem_file.exists():
            try:
                memories = len(json.loads(mem_file.read_text()))
            except (json.JSONDecodeError, OSError):
                memories = 0
        dec_file = mnemo_dir / "decisions.json"
        if dec_file.exists():
            try:
                decisions = len(json.loads(dec_file.read_text()))
            except (json.JSONDecodeError, OSError):
                decisions = 0
        graph_file = mnemo_dir / "graph_meta.json"
        if graph_file.exists():
            try:
                meta = json.loads(graph_file.read_text())
                graph_nodes = meta.get("nodes", 0)
            except (json.JSONDecodeError, OSError):
                graph_nodes = 0
        for f in mnemo_dir.rglob("*"):
            if f.is_file():
                try:
                    size_kb = f.stat().st_size / 1024
                    dir_size_kb += size_kb
                    rel = str(f.relative_to(mnemo_dir))
                    disk_breakdown[rel] = round(size_kb, 1)
                    if size_kb > 50 * 1024:
                        warnings.append(f"Large file: {rel} ({size_kb / 1024:.1f} MB)")
                except OSError:
                    continue  # Skip unreadable files
        if dir_size_kb > 100 * 1024:
            warnings.append(f"Total .mnemo/ size exceeds 100MB ({dir_size_kb / 1024:.1f} MB)")

    from ..utils.circuit_breaker import CircuitBreaker
    from ..vector_index import _breaker
    chromadb_status = _breaker.state

    result = {
        "memory_mb": mem_mb,
        "memories": memories,
        "decisions": decisions,
        "graph_nodes": graph_nodes,
        "chromadb_status": chromadb_status,
        "mnemo_dir_size_kb": dir_size_kb,
        "disk_breakdown": disk_breakdown,
    }
    if warnings:
        result["warnings"] = warnings
    return result


def calculate_health(repo_root: Path) -> str:
    """Calculate code health metrics for the project."""
    lines = ["# Code Health Report\n"]

    # System health section
    sh = system_health(repo_root)
    lines.append("## System Health")
    lines.append(f"- **Process memory:** {sh['memory_mb']:.1f} MB")
    lines.append(f"- **Memories:** {sh['memories']}")
    lines.append(f"- **Decisions:** {sh['decisions']}")
    lines.append(f"- **Graph nodes:** {sh['graph_nodes']}")
    lines.append(f"- **ChromaDB:** {sh['chromadb_status']}")
    lines.append(f"- **.mnemo/ size:** {sh['mnemo_dir_size_kb']:.1f} KB")
    lines.append("")

    hotspots: list[tuple[str, int, int, int]] = []  # (file, complexity, methods, lines)

    for ext, language in SUPPORTED_EXTENSIONS.items():
        for src_file in repo_root.rglob(f"*{ext}"):
            if _should_ignore(src_file) or "test" in str(src_file).lower():
                continue
            try:
                content = src_file.read_text(errors="replace")
            except (OSError, PermissionError):
                continue

            if len(content) < 100:
                continue

            rel = str(src_file.relative_to(repo_root))
            complexity = _estimate_complexity(content, language)
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
