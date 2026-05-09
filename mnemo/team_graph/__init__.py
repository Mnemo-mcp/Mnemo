"""Team Knowledge Graph — who knows what, based on git history."""

from __future__ import annotations

from pathlib import Path
from collections import defaultdict

from ..config import IGNORE_DIRS


def _should_ignore(path: str) -> bool:
    return any(part in IGNORE_DIRS for part in path.split("/"))


def build_team_graph(repo_root: Path) -> dict[str, dict]:
    """Build expertise map from git history."""
    try:
        from git import Repo
        repo = Repo(repo_root)
    except Exception:
        return {}

    # author → {service: commit_count}
    expertise: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    # file → last author
    last_touch: dict[str, str] = {}

    try:
        for commit in repo.iter_commits(max_count=500, no_merges=True):
            author = commit.author.name
            for file_path in commit.stats.files:
                if _should_ignore(file_path):
                    continue
                parts = file_path.split("/")
                service = parts[0] if len(parts) > 1 else "root"
                expertise[author][service] += 1
                if file_path not in last_touch:
                    last_touch[file_path] = author
    except Exception:
        pass

    return {
        "expertise": dict(expertise),
        "last_touch": last_touch,
    }


def get_experts(repo_root: Path, query: str = "") -> str:
    """Find who has expertise in a specific area."""
    graph = build_team_graph(repo_root)
    if not graph:
        return "No git history available for team analysis."

    expertise = graph.get("expertise", {})
    query_lower = query.lower()

    lines = []
    if query:
        lines.append(f"# Experts for '{query}'\n")
        # Find authors with most commits in matching services
        scores: list[tuple[str, int]] = []
        for author, services in expertise.items():
            score = sum(count for svc, count in services.items() if query_lower in svc.lower())
            if score > 0:
                scores.append((author, score))
        scores.sort(key=lambda x: -x[1])
        if scores:
            for author, count in scores[:10]:
                lines.append(f"- **{author}** — {count} commits")
        else:
            lines.append(f"No experts found for '{query}'.")
    else:
        lines.append("# Team Knowledge Map\n")
        for author in sorted(expertise.keys()):
            services = expertise[author]
            top = sorted(services.items(), key=lambda x: -x[1])[:3]
            areas = ", ".join(f"{svc} ({count})" for svc, count in top)
            lines.append(f"- **{author}** — {areas}")

    return "\n".join(lines)


def who_last_touched(repo_root: Path, filepath: str) -> str:
    """Find who last modified a file."""
    graph = build_team_graph(repo_root)
    last_touch = graph.get("last_touch", {})

    matches = [(f, author) for f, author in last_touch.items() if filepath.lower() in f.lower()]

    if not matches:
        return f"No git history for '{filepath}'."

    lines = [f"# Last touched: '{filepath}'\n"]
    for f, author in matches[:10]:
        lines.append(f"- **{f}** → {author}")
    return "\n".join(lines)
