"""Code Intelligence — architecture graph, dependencies, patterns, ownership."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..config import IGNORE_DIRS, mnemo_path
from ..retrieval import semantic_query
from ..sprint import get_current_task


def _should_ignore(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)


# --- Architecture Graph (service-to-service calls) ---

def detect_service_calls(repo_root: Path) -> dict[str, list[str]]:
    """Detect HTTP client calls between services by scanning for HttpClient, base URLs, etc."""
    graph: dict[str, set[str]] = {}

    for cs_file in repo_root.rglob("*.cs"):
        if _should_ignore(cs_file):
            continue
        try:
            content = cs_file.read_text(errors="replace")
        except (OSError, PermissionError):
            continue

        # Identify which service this file belongs to
        parts = cs_file.relative_to(repo_root).parts
        service = parts[0] if len(parts) > 1 else "root"
        if service not in graph:
            graph[service] = set()

        # Detect outbound HTTP calls
        urls = re.findall(r'["\']https?://[^"\']+["\']', content)
        base_urls = re.findall(r'BaseAddress\s*=\s*[^;]+', content)
        http_clients = re.findall(r'HttpClient|IHttpClientFactory|RestClient', content)

        for url in urls:
            # Try to identify target service from URL
            for known_svc in ["eligibility", "isauth", "providersearch", "servicereview", "auditlog", "mockdb"]:
                if known_svc in url.lower():
                    graph[service].add(known_svc)

    return {k: sorted(v) for k, v in graph.items() if v}


# --- Dependency Map ---

def detect_dependencies(repo_root: Path) -> dict[str, list[str]]:
    """Parse .csproj, package.json, requirements.txt for dependencies."""
    deps: dict[str, list[str]] = {}

    # .csproj files (NuGet)
    for csproj in repo_root.rglob("*.csproj"):
        if _should_ignore(csproj):
            continue
        try:
            content = csproj.read_text(errors="replace")
        except (OSError, PermissionError):
            continue
        packages = re.findall(r'<PackageReference\s+Include="([^"]+)"(?:\s+Version="([^"]*)")?', content)
        if packages:
            name = csproj.stem
            deps[name] = [f"{pkg} {ver}".strip() for pkg, ver in packages]

    # package.json
    for pkg_json in repo_root.rglob("package.json"):
        if _should_ignore(pkg_json):
            continue
        try:
            data = json.loads(pkg_json.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        all_deps = {}
        all_deps.update(data.get("dependencies", {}))
        all_deps.update(data.get("devDependencies", {}))
        if all_deps:
            name = data.get("name", pkg_json.parent.name)
            deps[name] = [f"{k} {v}" for k, v in all_deps.items()]

    return deps


# --- Pattern Detection ---

def detect_patterns(repo_root: Path) -> list[str]:
    """Detect common code patterns and conventions."""
    patterns: list[str] = []
    
    # Check for common .NET patterns
    controllers = list(repo_root.rglob("*Controller.cs"))
    if controllers:
        # Check what they inherit from
        for c in controllers[:3]:
            try:
                content = c.read_text(errors="replace")
                if "ControllerBase" in content:
                    patterns.append("Controllers inherit from ControllerBase (API controllers, no views)")
                    break
                elif "Controller" in content:
                    patterns.append("Controllers inherit from Controller (MVC with views)")
                    break
            except (OSError, PermissionError):
                continue

    # Check for repository pattern
    repos = list(repo_root.rglob("*Repository.cs"))
    interfaces = list(repo_root.rglob("I*Repository.cs"))
    if repos and interfaces:
        patterns.append(f"Repository pattern with interfaces ({len(interfaces)} interfaces, {len(repos)} implementations)")

    # Check for handler/strategy pattern
    handlers = list(repo_root.rglob("*Handler.cs"))
    if len(handlers) > 2:
        patterns.append(f"Strategy/Handler pattern ({len(handlers)} handlers found)")

    # Check for DI registration
    for f in repo_root.rglob("Program.cs"):
        if _should_ignore(f):
            continue
        try:
            content = f.read_text(errors="replace")
            if "AddScoped" in content or "AddTransient" in content or "AddSingleton" in content:
                patterns.append("Dependency injection via built-in .NET DI container")
                break
        except (OSError, PermissionError):
            continue

    # Check for test patterns
    test_files = list(repo_root.rglob("*Tests.cs"))
    if test_files:
        try:
            sample = test_files[0].read_text(errors="replace")
            if "xUnit" in sample or "[Fact]" in sample:
                patterns.append("Testing with xUnit ([Fact], [Theory])")
            elif "[Test]" in sample:
                patterns.append("Testing with NUnit")
            if "Moq" in sample or "Mock<" in sample:
                patterns.append("Mocking with Moq")
            if "FluentAssertions" in sample:
                patterns.append("Assertions with FluentAssertions")
        except (OSError, PermissionError):
            pass

    # Check for CosmosDB
    cosmos_files = [f for f in repo_root.rglob("*.cs") if not _should_ignore(f)]
    for f in cosmos_files[:50]:
        try:
            if "CosmosClient" in f.read_text(errors="replace"):
                patterns.append("Data layer: Azure CosmosDB")
                break
        except (OSError, PermissionError):
            continue

    return patterns


def classify_architecture(repo_root: Path) -> list[dict[str, Any]]:
    """Classify high-level architecture styles with evidence."""
    findings: list[dict[str, Any]] = []
    paths = [p for p in repo_root.rglob("*") if not _should_ignore(p)]
    names = [str(p).lower() for p in paths]
    text_blob = " ".join(names)

    checks = [
        ("Clean Architecture", ["domain", "application", "infrastructure", "presentation"]),
        ("CQRS", ["command", "query", "handler"]),
        ("Hexagonal", ["ports", "adapters"]),
        ("Event-Driven", ["event", "consumer", "producer"]),
        ("Microservices", ["docker-compose", "helm", "service", "gateway"]),
    ]
    for arch, signals in checks:
        matched = [signal for signal in signals if signal in text_blob]
        if matched:
            findings.append(
                {
                    "name": arch,
                    "confidence": round(len(matched) / len(signals), 2),
                    "evidence": matched,
                }
            )
    return sorted(findings, key=lambda item: item["confidence"], reverse=True)


# --- Similar Implementations ---

def find_similar(repo_root: Path, query: str) -> list[dict[str, str]]:
    """Find files with similar naming patterns to help implement new features."""
    query_lower = query.lower()
    semantic_hits = semantic_query(repo_root, "code", query, limit=20)
    if semantic_hits:
        results = []
        for hit in semantic_hits:
            meta = hit.get("metadata", {})
            results.append(
                {
                    "file": str(meta.get("path", "")),
                    "class": str(meta.get("symbol", "")),
                }
            )
        return results

    similar: list[dict[str, str]] = []

    # Find files matching the pattern
    for cs_file in repo_root.rglob("*.cs"):
        if _should_ignore(cs_file):
            continue
        name = cs_file.stem.lower()
        # Match by suffix pattern (e.g. "Handler" finds all *Handler.cs)
        if query_lower in name:
            rel = str(cs_file.relative_to(repo_root))
            try:
                content = cs_file.read_text(errors="replace")
                # Get class declaration line
                match = re.search(r'(public\s+class\s+\w+[^{]*)', content)
                sig = match.group(1).strip() if match else ""
                similar.append({"file": rel, "class": sig})
            except (OSError, PermissionError):
                similar.append({"file": rel, "class": ""})

    return similar[:20]


def context_for_active_task(repo_root: Path, query: str = "") -> str:
    """Retrieve semantic context using the active task as a relevance hint."""
    active_task_markdown = get_current_task(repo_root)
    if active_task_markdown.startswith("No active task"):
        return active_task_markdown

    search_query = query.strip() or active_task_markdown
    hits = semantic_query(repo_root, "code", search_query, limit=10)
    if not hits:
        return "No semantic context found for the current task."

    lines = ["# Context for Active Task", "", "## Active Task", active_task_markdown, "", "## Relevant Code"]
    for hit in hits:
        meta = hit.get("metadata", {})
        lines.append(f"- `{meta.get('path', '')}` :: `{meta.get('symbol', '')}`")
    return "\n".join(lines)


# --- Ownership (git blame stats) ---

def detect_ownership(repo_root: Path) -> dict[str, str]:
    """Detect code ownership from CODEOWNERS or git stats."""
    owners: dict[str, str] = {}

    # Check CODEOWNERS
    for codeowners_path in [
        repo_root / "CODEOWNERS",
        repo_root / ".github" / "CODEOWNERS",
        repo_root / "docs" / "CODEOWNERS",
    ]:
        if codeowners_path.exists():
            try:
                for line in codeowners_path.read_text().splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split()
                        if len(parts) >= 2:
                            owners[parts[0]] = " ".join(parts[1:])
            except (OSError, PermissionError):
                pass
            break

    return owners


# --- Main intelligence report ---

def generate_intelligence(repo_root: Path) -> str:
    """Generate a full code intelligence report as markdown."""
    lines = ["# Code Intelligence\n"]

    # Patterns
    patterns = detect_patterns(repo_root)
    if patterns:
        lines.append("## Patterns & Conventions")
        for p in patterns:
            lines.append(f"- {p}")
        lines.append("")

    # Architecture
    graph = detect_service_calls(repo_root)
    if graph:
        lines.append("## Service Architecture")
        for svc, targets in sorted(graph.items()):
            lines.append(f"- **{svc}** → {', '.join(targets)}")
        lines.append("")

    # Dependencies
    deps = detect_dependencies(repo_root)
    if deps:
        lines.append("## Dependencies")
        for project, pkgs in sorted(deps.items()):
            lines.append(f"**{project}:** {', '.join(pkgs[:10])}")
            if len(pkgs) > 10:
                lines.append(f"  ... and {len(pkgs) - 10} more")
        lines.append("")

    # Ownership
    owners = detect_ownership(repo_root)
    if owners:
        lines.append("## Code Ownership")
        for path, owner in owners.items():
            lines.append(f"- `{path}` → {owner}")
        lines.append("")

    architectures = classify_architecture(repo_root)
    if architectures:
        lines.append("## Architecture Classification")
        for arch in architectures:
            evidence = ", ".join(arch["evidence"])
            lines.append(f"- **{arch['name']}** (confidence {arch['confidence']}) — evidence: {evidence}")
        lines.append("")

    return "\n".join(lines)
