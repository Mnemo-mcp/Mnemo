"""Relationship extraction — detects structural edges from parsed code."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from . import Edge
from ..config import IGNORE_DIRS, SUPPORTED_EXTENSIONS, should_ignore


def extract_call_edges(repo_root: Path, file_path: str, source: str, class_names: set[str]) -> list[Edge]:
    """Detect calls from methods in this file to other known classes."""
    edges = []
    file_id = f"file:{file_path}"

    for class_name in class_names:
        # Skip self-references and very short names (likely false positives)
        if len(class_name) < 3:
            continue
        # Check for usage patterns: new ClassName(, _className., IClassName, ClassName.Method
        patterns = [
            rf'\bnew\s+{re.escape(class_name)}\s*\(',
            rf'\b{re.escape(class_name)}\s*\.\w+',
            rf'<{re.escape(class_name)}>',
            rf'\b{re.escape(class_name)}\s+\w+',  # Type declaration
        ]
        for pattern in patterns:
            if re.search(pattern, source):
                edges.append(Edge(source=file_id, target=f"class:{class_name}", type="calls"))
                break

    return edges


def extract_dependency_edges(repo_root: Path) -> list[tuple[str, str, dict]]:
    """Extract package dependencies from project files. Returns (service, package, metadata)."""
    deps = []

    # .csproj (NuGet)
    for csproj in repo_root.rglob("*.csproj"):
        if should_ignore(csproj):
            continue
        try:
            content = csproj.read_text(errors="replace")
        except (OSError, PermissionError):
            continue
        service = csproj.relative_to(repo_root).parts[0] if len(csproj.relative_to(repo_root).parts) > 1 else csproj.stem
        for match in re.finditer(r'<PackageReference\s+Include="([^"]+)"(?:\s+Version="([^"]*)")?', content):
            pkg, ver = match.group(1), match.group(2) or ""
            deps.append((service, pkg, {"version": ver}))

    # package.json
    for pkg_json in repo_root.rglob("package.json"):
        if should_ignore(pkg_json):
            continue
        try:
            data = json.loads(pkg_json.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        service = pkg_json.relative_to(repo_root).parts[0] if len(pkg_json.relative_to(repo_root).parts) > 1 else data.get("name", pkg_json.parent.name)
        for pkg, ver in {**data.get("dependencies", {}), **data.get("devDependencies", {})}.items():
            deps.append((service, pkg, {"version": ver}))

    # requirements.txt
    for req_file in repo_root.rglob("requirements.txt"):
        if should_ignore(req_file):
            continue
        try:
            lines = req_file.read_text().splitlines()
        except (OSError, PermissionError):
            continue
        service = req_file.relative_to(repo_root).parts[0] if len(req_file.relative_to(repo_root).parts) > 1 else "root"
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                pkg = re.split(r'[>=<!\[]', line)[0].strip()
                if pkg:
                    deps.append((service, pkg, {}))

    return deps


def extract_ownership_edges(repo_root: Path) -> list[tuple[str, str, int]]:
    """Extract ownership from git log. Returns (person, file_path, commit_count)."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "shortlog", "-sn", "--all", "--no-merges"],
            cwd=repo_root, capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    # Get per-file ownership (top contributor per top-level dir)
    ownership = []
    try:
        result = subprocess.run(
            ["git", "log", "--format=%aN", "--name-only", "--diff-filter=ACMR", "-100"],
            cwd=repo_root, capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    # Parse: author line followed by file lines
    file_authors: dict[str, dict[str, int]] = {}
    current_author = ""
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if "/" not in line and "." not in line:
            current_author = line
        elif current_author:
            service = line.split("/")[0]
            key = service
            if key not in file_authors:
                file_authors[key] = {}
            file_authors[key][current_author] = file_authors[key].get(current_author, 0) + 1

    for service, authors in file_authors.items():
        if authors:
            top_author = max(authors, key=authors.get)
            ownership.append((top_author, service, authors[top_author]))

    return ownership
