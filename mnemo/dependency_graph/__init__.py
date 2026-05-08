"""Dependency Graph — map service-to-service relationships and impact analysis."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..config import IGNORE_DIRS, mnemo_path


def _should_ignore(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)


def build_dependency_graph(repo_root: Path) -> dict[str, dict]:
    """Build a graph of service dependencies from code analysis."""
    graph: dict[str, dict] = {}

    # Detect services (top-level directories with Program.cs or .csproj)
    services = set()
    for f in repo_root.rglob("Program.cs"):
        if not _should_ignore(f):
            services.add(f.relative_to(repo_root).parts[0])
    for f in repo_root.rglob("*.csproj"):
        if not _should_ignore(f):
            services.add(f.relative_to(repo_root).parts[0])

    for service in services:
        svc_path = repo_root / service
        graph[service] = {"calls": [], "called_by": [], "packages": [], "internal_deps": []}

        for cs_file in svc_path.rglob("*.cs"):
            if _should_ignore(cs_file):
                continue
            try:
                content = cs_file.read_text(errors="replace")
            except (OSError, PermissionError):
                continue

            # Detect HTTP calls to other services
            for other_svc in services:
                if other_svc == service:
                    continue
                if other_svc.lower() in content.lower():
                    if other_svc not in graph[service]["calls"]:
                        graph[service]["calls"].append(other_svc)

            # Detect project references
            refs = re.findall(r'using\s+([\w.]+Service)', content)
            for ref in refs:
                if ref not in graph[service]["internal_deps"]:
                    graph[service]["internal_deps"].append(ref)

        # Parse .csproj for package deps
        for csproj in svc_path.rglob("*.csproj"):
            if _should_ignore(csproj):
                continue
            try:
                content = csproj.read_text(errors="replace")
                packages = re.findall(r'<PackageReference\s+Include="([^"]+)"', content)
                graph[service]["packages"] = packages
            except (OSError, PermissionError):
                pass

    # Build reverse graph (called_by)
    for svc, info in graph.items():
        for target in info["calls"]:
            if target in graph:
                if svc not in graph[target]["called_by"]:
                    graph[target]["called_by"].append(svc)

    return graph


def impact_analysis(repo_root: Path, service_or_file: str) -> str:
    """Answer: what breaks if I change this?"""
    graph = build_dependency_graph(repo_root)
    query = service_or_file.lower()

    # Find matching service
    target_svc = None
    for svc in graph:
        if query in svc.lower():
            target_svc = svc
            break

    if not target_svc:
        return f"No service matching '{service_or_file}' found."

    info = graph[target_svc]
    lines = [f"# Impact Analysis: {target_svc}\n"]

    if info["called_by"]:
        lines.append("## Services that depend on this (will break if you change the API):")
        for dep in info["called_by"]:
            lines.append(f"- **{dep}**")
        lines.append("")

    if info["calls"]:
        lines.append("## Services this depends on:")
        for dep in info["calls"]:
            lines.append(f"- {dep}")
        lines.append("")

    if not info["called_by"] and not info["calls"]:
        lines.append("No known dependencies. This service appears isolated.")

    return "\n".join(lines)


def format_graph(repo_root: Path) -> str:
    """Format the full dependency graph as markdown."""
    graph = build_dependency_graph(repo_root)
    if not graph:
        return "No services detected."

    lines = ["# Dependency Graph\n"]
    for svc in sorted(graph.keys()):
        info = graph[svc]
        calls = f" → {', '.join(info['calls'])}" if info["calls"] else ""
        called_by = f" ← {', '.join(info['called_by'])}" if info["called_by"] else ""
        lines.append(f"**{svc}**{calls}{called_by}")
        if info["packages"]:
            lines.append(f"  Packages: {', '.join(info['packages'][:5])}")
    return "\n".join(lines)
