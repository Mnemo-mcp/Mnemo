"""Onboarding Mode — generate a complete project overview for new developers."""

from __future__ import annotations

from pathlib import Path

from ..config import mnemo_path
from ..intelligence import detect_patterns, detect_dependencies, detect_service_calls
from ..api_discovery import discover_apis


def generate_onboarding(repo_root: Path) -> str:
    """Generate a comprehensive onboarding document for new team members."""
    lines = ["# Project Onboarding Guide\n"]

    # Project basics
    lines.append("## Overview")
    lines.append(f"Repository: `{repo_root.name}`")

    # Detect services
    services = set()
    for f in repo_root.rglob("Program.cs"):
        from ..config import IGNORE_DIRS
        if not any(part in IGNORE_DIRS for part in f.relative_to(repo_root).parts):
            services.add(f.relative_to(repo_root).parts[0])
    if services:
        lines.append(f"Services: {len(services)} microservices")
        for svc in sorted(services):
            lines.append(f"- **{svc}**")
    lines.append("")

    # Patterns
    patterns = detect_patterns(repo_root)
    if patterns:
        lines.append("## Tech Stack & Patterns")
        for p in patterns:
            lines.append(f"- {p}")
        lines.append("")

    # Architecture
    graph = detect_service_calls(repo_root)
    if graph:
        lines.append("## Service Architecture")
        lines.append("How services communicate:")
        for svc, targets in sorted(graph.items()):
            lines.append(f"- **{svc}** calls → {', '.join(targets)}")
        lines.append("")

    # Key dependencies
    deps = detect_dependencies(repo_root)
    if deps:
        lines.append("## Key Dependencies")
        for project, pkgs in sorted(deps.items()):
            key_pkgs = [p for p in pkgs if any(k in p for k in ["Cosmos", "Azure", "Identity", "Polly", "Swagger"])]
            if key_pkgs:
                lines.append(f"**{project}:** {', '.join(key_pkgs[:5])}")
        lines.append("")

    # API endpoints summary
    lines.append("## API Endpoints")
    lines.append("Use `mnemo_discover_apis` for full details. Key services:")
    for svc in sorted(services):
        lines.append(f"- {svc}")
    lines.append("")

    # Getting started
    lines.append("## Getting Started")
    lines.append("1. Clone the repo")
    lines.append("2. Run `mnemo init` to set up project memory")
    lines.append("3. Ask Amazon Q: \"What does this project do?\"")
    lines.append("4. Ask: \"Show me the architecture\"")
    lines.append("5. Ask: \"I need to add a new [feature], show me similar implementations\"")
    lines.append("")

    # Knowledge base
    kb_path = mnemo_path(repo_root) / "knowledge"
    if kb_path.exists():
        kb_files = list(kb_path.rglob("*.md"))
        if kb_files:
            lines.append("## Team Knowledge")
            lines.append("Check `.mnemo/knowledge/` for:")
            for f in kb_files:
                lines.append(f"- {f.name}")
            lines.append("")

    return "\n".join(lines)
