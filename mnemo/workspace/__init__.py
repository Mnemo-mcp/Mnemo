"""Multi-repo workspace — link, discover, and query across repositories."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from ..config import mnemo_path

LINKS_FILE = "links.json"


def _links_path(repo_root: Path) -> Path:
    return mnemo_path(repo_root) / LINKS_FILE


def get_linked_repos(repo_root: Path) -> list[Path]:
    """Return resolved paths of all linked repos that exist and are initialized."""
    path = _links_path(repo_root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    linked: list[Path] = []
    for entry in data:
        repo_path = Path(entry["path"]).expanduser().resolve()
        if repo_path != repo_root.resolve() and (repo_path / ".mnemo").exists():
            linked.append(repo_path)
    return linked


def _save_links(repo_root: Path, links: list[dict[str, str]]) -> None:
    path = _links_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(links, indent=2), encoding="utf-8")


def link_repo(repo_root: Path, target: Path) -> str:
    """Link a sibling repo for cross-repo queries."""
    target = target.expanduser().resolve()
    if not target.exists():
        return f"Path does not exist: {target}"
    if not (target / ".git").exists() and not (target / ".mnemo").exists():
        return f"Not a repo: {target} (no .git or .mnemo found)"

    existing = get_linked_repos(repo_root)
    if target in [r.resolve() for r in existing]:
        return f"Already linked: {target.name}"

    # Load raw data to append
    path = _links_path(repo_root)
    data: list[dict[str, str]] = []
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = []

    data.append({"name": target.name, "path": str(target)})
    _save_links(repo_root, data)

    initialized = (target / ".mnemo").exists()
    status = "✓ indexed" if initialized else "⚠ needs `mnemo init`"
    return f"Linked: {target.name} ({status})"


def unlink_repo(repo_root: Path, name: str) -> str:
    """Remove a linked repo by name or path."""
    path = _links_path(repo_root)
    if not path.exists():
        return "No linked repos."
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "No linked repos."

    name_lower = name.lower()
    filtered = [e for e in data if e.get("name", "").lower() != name_lower and name_lower not in e.get("path", "").lower()]
    if len(filtered) == len(data):
        return f"No linked repo matching '{name}'."
    _save_links(repo_root, filtered)
    return f"Unlinked: {name}"


def discover_repos(repo_root: Path, search_dir: Path, auto_init: bool = False) -> str:
    """Auto-discover and link all repos under a directory. Optionally init uninitialized ones."""
    search_dir = search_dir.expanduser().resolve()
    if not search_dir.exists():
        return f"Directory not found: {search_dir}"

    found: list[Path] = []
    for child in search_dir.iterdir():
        if not child.is_dir():
            continue
        if child.resolve() == repo_root.resolve():
            continue
        if (child / ".git").exists():
            found.append(child)

    if not found:
        return f"No git repos found under {search_dir}"

    results = []
    for repo in sorted(found):
        result = link_repo(repo_root, repo)
        results.append(result)

        # Auto-init if requested and not yet initialized
        if auto_init and not (repo / ".mnemo").exists():
            try:
                from ..init import init
                import sys
                sys.stderr.write(f"  Initializing {repo.name}...\n")
                init(repo)
                results.append(f"  ✓ Initialized {repo.name}")
            except Exception as e:
                results.append(f"  ✗ Failed to init {repo.name}: {e}")

    return "\n".join(results)


def format_links(repo_root: Path) -> str:
    """Show all linked repos with status."""
    path = _links_path(repo_root)
    if not path.exists():
        return "No linked repos. Use `mnemo link <path>` or `mnemo link --discover <dir>`."

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "No linked repos."

    if not data:
        return "No linked repos."

    lines = [f"# Linked Repos ({len(data)})\n"]
    for entry in data:
        name = entry.get("name", "unknown")
        repo_path = Path(entry.get("path", ""))
        exists = repo_path.exists()
        initialized = (repo_path / ".mnemo").exists() if exists else False

        if not exists:
            status = "✗ path not found"
        elif initialized:
            status = "✓ indexed"
        else:
            status = "⚠ needs `mnemo init`"

        lines.append(f"- **{name}**  {repo_path}  {status}")

    return "\n".join(lines)


def cross_repo_semantic_query(
    repo_root: Path, namespace: str, query: str, limit: int = 10
) -> list[dict[str, Any]]:
    """Query this repo + all linked repos, merge and rank results."""
    from ..retrieval import semantic_query

    # Query local repo first
    results = semantic_query(repo_root, namespace, query, limit=limit)
    for r in results:
        r["repo"] = repo_root.name

    # Query linked repos
    for linked in get_linked_repos(repo_root):
        try:
            linked_results = semantic_query(linked, namespace, query, limit=limit // 2)
            for r in linked_results:
                r["repo"] = linked.name
            results.extend(linked_results)
        except Exception as exc:
            print(f"[mnemo] Failed to query linked repo {linked.name}: {exc}", file=sys.stderr)
            continue

    # Sort by score descending, deduplicate by id
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for r in sorted(results, key=lambda x: x.get("score", 0), reverse=True):
        rid = r.get("id", "")
        if rid not in seen:
            seen.add(rid)
            unique.append(r)

    return unique[:limit]


def cross_repo_impact(repo_root: Path, query: str) -> str:
    """Check all linked repos for code that depends on the queried service/file."""
    from ..retrieval import semantic_query

    lines = [f"# Cross-Repo Impact: '{query}'\n"]
    lines.append("## This Repo")

    local_hits = semantic_query(repo_root, "code", query, limit=5)
    if local_hits:
        for hit in local_hits:
            meta = hit.get("metadata", {})
            lines.append(f"- `{meta.get('path', '')}` :: `{meta.get('symbol', '')}`")
    else:
        lines.append("- No matches in this repo")

    linked = get_linked_repos(repo_root)
    if not linked:
        lines.append("\nNo linked repos. Use `mnemo link` to enable cross-repo impact analysis.")
        return "\n".join(lines)

    for linked_repo in linked:
        lines.append(f"\n## {linked_repo.name}")
        try:
            hits = semantic_query(linked_repo, "code", query, limit=5)
            if hits:
                for hit in hits:
                    meta = hit.get("metadata", {})
                    lines.append(f"- `{meta.get('path', '')}` :: `{meta.get('symbol', '')}`")
            else:
                lines.append("- No matches")
        except Exception as exc:
            lines.append(f"- ⚠ Could not query (run `mnemo init` in that repo): {exc}")

    return "\n".join(lines)
