"""API Discovery — uses engine/ graph + OpenAPI spec parsing."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..config import IGNORE_DIRS


def _should_ignore(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)


def _find_openapi_specs(repo_root: Path) -> list[Path]:
    """Find OpenAPI/Swagger spec files."""
    specs = []
    for pattern in ("swagger.json", "openapi.json", "swagger.yaml", "openapi.yaml"):
        for f in repo_root.rglob(pattern):
            if not _should_ignore(f):
                specs.append(f)
    return specs


def _parse_openapi(spec_path: Path) -> dict[str, Any] | None:
    """Parse an OpenAPI spec into a compact summary."""
    try:
        content = spec_path.read_text()
        if spec_path.suffix in (".yaml", ".yml"):
            import yaml
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)
    except Exception:
        return None

    if not data or not isinstance(data, dict):
        return None

    info = data.get("info", {})
    paths = data.get("paths", {})
    endpoints = []
    for path, methods in paths.items():
        for method, details in methods.items():
            if method in ("get", "post", "put", "delete", "patch"):
                endpoints.append({"method": method.upper(), "path": path, "summary": details.get("summary", "")})
    return {"title": info.get("title", spec_path.stem), "version": info.get("version", ""), "endpoints": endpoints}


def _detect_endpoints_from_graph(repo_root: Path) -> list[dict[str, Any]]:
    """Detect API endpoints from controller files indexed in graph."""
    from ..engine.db import open_db, get_db_path

    if not get_db_path(repo_root).exists():
        return []

    _, conn = open_db(repo_root)
    endpoints = []

    # Find controller files and their functions
    result = conn.execute("""
        MATCH (f:File)-[:FILE_DEFINES_CLASS]->(c:Class)
        WHERE f.path CONTAINS 'Controller'
        AND NOT f.path CONTAINS 'test'
        RETURN f.path, c.name
    """)
    controller_files: list[tuple[str, str]] = []
    while result.has_next():
        row = result.get_next()
        controller_files.append((row[0], row[1]))

    # For each controller, read source to extract route attributes
    for file_path, class_name in controller_files:
        fp = repo_root / file_path
        if not fp.exists():
            continue
        try:
            content = fp.read_text(errors="replace")
        except OSError:
            continue

        service = file_path.split("/")[0]
        class_route = ""
        route_match = re.search(r'\[Route\("([^"]+)"\)\]', content)
        if route_match:
            class_route = route_match.group(1)

        for match in re.finditer(
            r'\[(Http(Get|Post|Put|Delete|Patch))(?:\("([^"]*)"\))?\]\s*(?:\[.*?\]\s*)*public\s+(?:async\s+)?\S+\s+(\w+)',
            content, re.DOTALL
        ):
            method = match.group(2).upper()
            route = match.group(3) or ""
            func_name = match.group(4)
            full_path = f"/{class_route}/{route}".replace("//", "/").rstrip("/")
            full_path = re.sub(r'\[controller\]', class_name.replace('Controller', '').lower(), full_path)
            endpoints.append({"service": service, "method": method, "path": full_path, "handler": func_name})

    return endpoints


def discover_apis(repo_root: Path) -> str:
    """Discover all APIs in the repo."""
    lines = ["# API Discovery\n"]

    specs = _find_openapi_specs(repo_root)
    if specs:
        lines.append("## OpenAPI Specifications\n")
        for spec_path in specs:
            parsed = _parse_openapi(spec_path)
            if parsed:
                lines.append(f"### {parsed['title']} (v{parsed['version']})")
                for ep in parsed["endpoints"]:
                    lines.append(f"- `{ep['method']} {ep['path']}` {ep['summary']}")
                lines.append("")

    controller_endpoints = _detect_endpoints_from_graph(repo_root)
    if controller_endpoints:
        lines.append("## Controller Endpoints\n")
        by_service: dict[str, list] = {}
        for ep in controller_endpoints:
            by_service.setdefault(ep["service"], []).append(ep)
        for svc in sorted(by_service):
            lines.append(f"### {svc}")
            for ep in by_service[svc]:
                lines.append(f"- `{ep['method']} {ep['path']}` → {ep['handler']}()")
            lines.append("")

    if len(lines) <= 2:
        return "No APIs discovered."
    return "\n".join(lines)


def search_api(repo_root: Path, query: str) -> str:
    """Search discovered APIs by query."""
    full = discover_apis(repo_root)
    if "No APIs" in full:
        return f"No APIs matching '{query}'."
    query_lower = query.lower()
    lines = [ln for ln in full.split("\n") if query_lower in ln.lower() or ln.startswith("#")]
    return "\n".join(lines) if any(not ln.startswith("#") for ln in lines) else f"No APIs matching '{query}'."
