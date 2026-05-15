"""Code Intelligence — architecture graph, dependencies, patterns, ownership."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..config import IGNORE_DIRS, SUPPORTED_EXTENSIONS, mnemo_path, should_ignore
from ..retrieval import semantic_query
from ..sprint import get_current_task


def _should_ignore(path: Path) -> bool:
    return should_ignore(path)


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

        for url in urls:
            # Try to identify target service from URL
            for known_svc in ["eligibility", "isauth", "providersearch", "servicereview", "auditlog", "mockdb"]:
                if known_svc in url.lower():
                    graph[service].add(known_svc)

    return {k: sorted(v) for k, v in graph.items() if v}


# --- Dependency Map ---

def detect_dependencies(repo_root: Path) -> dict[str, list[str]]:
    """Parse .csproj, package.json, requirements.txt for dependencies."""
    import os

    deps: dict[str, list[str]] = {}

    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for filename in filenames:
            filepath = Path(dirpath) / filename

            if filename.endswith(".csproj"):
                try:
                    content = filepath.read_text(errors="replace")
                except (OSError, PermissionError):
                    continue
                packages = re.findall(r'<PackageReference\s+Include="([^"]+)"(?:\s+Version="([^"]*)")?', content)
                if packages:
                    deps[filepath.stem] = [f"{pkg} {ver}".strip() for pkg, ver in packages]

            elif filename == "package.json":
                try:
                    data = json.loads(filepath.read_text())
                except (OSError, json.JSONDecodeError):
                    continue
                all_deps = {}
                all_deps.update(data.get("dependencies", {}))
                all_deps.update(data.get("devDependencies", {}))
                if all_deps:
                    name = data.get("name", filepath.parent.name)
                    deps[name] = [f"{k} {v}" for k, v in all_deps.items()]

    return deps


# --- Pattern Detection ---

def detect_patterns(repo_root: Path) -> list[str]:
    """Detect common code patterns and conventions."""
    import os

    patterns: list[str] = []

    # Single walk to collect categorized files
    controllers: list[Path] = []
    repos: list[Path] = []
    interfaces: list[Path] = []
    handlers: list[Path] = []
    program_files: list[Path] = []
    test_files: list[Path] = []
    cs_files: list[Path] = []

    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for filename in filenames:
            if not filename.endswith(".cs"):
                continue
            filepath = Path(dirpath) / filename
            if filename.endswith("Controller.cs"):
                controllers.append(filepath)
            if filename.endswith("Repository.cs"):
                if filename.startswith("I"):
                    interfaces.append(filepath)
                else:
                    repos.append(filepath)
            if filename.endswith("Handler.cs"):
                handlers.append(filepath)
            if filename == "Program.cs":
                program_files.append(filepath)
            if filename.endswith("Tests.cs"):
                test_files.append(filepath)
            cs_files.append(filepath)

    # Check controller patterns
    if controllers:
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

    if repos and interfaces:
        patterns.append(f"Repository pattern with interfaces ({len(interfaces)} interfaces, {len(repos)} implementations)")

    if len(handlers) > 2:
        patterns.append(f"Strategy/Handler pattern ({len(handlers)} handlers found)")

    # Check for DI registration
    for f in program_files:
        try:
            content = f.read_text(errors="replace")
            if "AddScoped" in content or "AddTransient" in content or "AddSingleton" in content:
                patterns.append("Dependency injection via built-in .NET DI container")
                break
        except (OSError, PermissionError):
            continue

    # Check for test patterns
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
    for f in cs_files[:50]:
        try:
            if "CosmosClient" in f.read_text(errors="replace"):
                patterns.append("Data layer: Azure CosmosDB")
                break
        except (OSError, PermissionError):
            continue

    return patterns


def classify_architecture(repo_root: Path) -> list[dict[str, Any]]:
    """Classify high-level architecture styles with evidence."""
    import os

    findings: list[dict[str, Any]] = []
    # Single os.walk instead of rglob("*")
    names: list[str] = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for name in dirnames + filenames:
            names.append(name.lower())
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


def detect_design_patterns_from_graph(repo_root: Path) -> list[dict[str, Any]]:
    """Detect design patterns from knowledge graph relationships (MNO-838)."""
    try:
        from .graph.local import LocalGraph
        graph = LocalGraph(repo_root)
        if not graph.exists():
            return []
    except Exception:
        return []

    patterns: list[dict[str, Any]] = []
    g = graph.graph

    # Strategy pattern: multiple classes implementing same interface
    interface_impls: dict[str, list[str]] = {}
    for src, tgt, data in g.edges(data=True):
        if data.get("type") == "implements":
            interface_impls.setdefault(tgt, []).append(src)

    for iface, impls in interface_impls.items():
        if len(impls) >= 3:
            iface_node = graph.get_node(iface)
            name = iface_node.name if iface_node else iface
            patterns.append({
                "pattern": "Strategy",
                "interface": name,
                "implementations": len(impls),
                "examples": [graph.get_node(i).name for i in impls[:5] if graph.get_node(i)],
            })

    # Template Method: class with inheritance chain
    inheritance_chains: dict[str, list[str]] = {}
    for src, tgt, data in g.edges(data=True):
        if data.get("type") == "inherits":
            inheritance_chains.setdefault(tgt, []).append(src)

    for base, children in inheritance_chains.items():
        if len(children) >= 2:
            base_node = graph.get_node(base)
            name = base_node.name if base_node else base
            patterns.append({
                "pattern": "Template Method / Inheritance",
                "base_class": name,
                "subclasses": len(children),
                "examples": [graph.get_node(c).name for c in children[:5] if graph.get_node(c)],
            })

    # Facade: service node with many outgoing 'contains' edges to files
    for nid, data in g.nodes(data=True):
        if data.get("type") == "service":
            out_count = sum(1 for _, _, d in g.out_edges(nid, data=True) if d.get("type") == "contains")
            if out_count >= 8:
                patterns.append({
                    "pattern": "Facade/Module",
                    "service": data.get("name", nid),
                    "file_count": out_count,
                })

    return patterns


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
                    "content": hit.get("content", "")[:300],
                }
            )
        return results

    similar: list[dict[str, str]] = []

    # Find files matching the pattern across all supported languages
    for ext in SUPPORTED_EXTENSIONS:
        for src_file in repo_root.rglob(f"*{ext}"):
            if _should_ignore(src_file):
                continue
            name = src_file.stem.lower()
            if query_lower in name:
                rel = str(src_file.relative_to(repo_root))
                try:
                    content = src_file.read_text(errors="replace")
                    # Get class declaration line (language-agnostic patterns)
                    match = (
                        re.search(r'(public\s+class\s+\w+[^{]*)', content)
                        or re.search(r'(class\s+\w+[^:]*:)', content)
                        or re.search(r'(func\s+\w+\s*\()', content)
                    )
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

    # Design patterns from graph (MNO-838)
    graph_patterns = detect_design_patterns_from_graph(repo_root)
    if graph_patterns:
        lines.append("## Design Patterns (from graph)")
        for p in graph_patterns:
            if p["pattern"] == "Strategy":
                lines.append(f"- **Strategy**: `{p['interface']}` ({p['implementations']} implementations: {', '.join(p['examples'])})")
            elif p["pattern"] == "Template Method / Inheritance":
                lines.append(f"- **Template Method**: `{p['base_class']}` ({p['subclasses']} subclasses: {', '.join(p['examples'])})")
            elif p["pattern"] == "Facade/Module":
                lines.append(f"- **Facade**: `{p['service']}` ({p['file_count']} files)")
        lines.append("")

    return "\n".join(lines)
