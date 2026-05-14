"""API Discovery — parse OpenAPI/Swagger specs and service endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..chunking import api_endpoint_chunk
from ..config import IGNORE_DIRS, mnemo_path
from ..retrieval import index_chunks, semantic_query


def _should_ignore(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)


def _find_openapi_specs(repo_root: Path) -> list[Path]:
    """Find OpenAPI/Swagger spec files."""
    specs = []
    patterns = ["swagger.json", "openapi.json", "swagger.yaml", "openapi.yaml"]

    for pattern in patterns:
        for f in repo_root.rglob(pattern):
            if not _should_ignore(f):
                specs.append(f)

    # Also check for specs in common locations
    for candidate in [
        repo_root / "docs" / "api",
        repo_root / "api",
        repo_root / "specs",
    ]:
        if candidate.exists():
            for f in candidate.rglob("*.json"):
                try:
                    data = json.loads(f.read_text())
                    if "openapi" in data or "swagger" in data:
                        specs.append(f)
                except (json.JSONDecodeError, OSError):
                    pass

    return specs


def _parse_openapi(spec_path: Path) -> dict[str, Any] | None:
    """Parse an OpenAPI spec into a compact summary."""
    try:
        content = spec_path.read_text()
        if spec_path.suffix in (".yaml", ".yml"):
            try:
                import yaml
                data = yaml.safe_load(content)
            except ImportError:
                return None
        else:
            data = json.loads(content)
    except (json.JSONDecodeError, OSError):
        return None

    if not data or not isinstance(data, dict):
        return None

    info = data.get("info", {})
    paths = data.get("paths", {})

    endpoints = []
    for path, methods in paths.items():
        for method, details in methods.items():
            if method in ("get", "post", "put", "delete", "patch"):
                endpoint = {
                    "method": method.upper(),
                    "path": path,
                    "summary": details.get("summary", details.get("operationId", "")),
                }
                # Get request body schema name
                req_body = details.get("requestBody", {})
                if req_body:
                    content_types = req_body.get("content", {})
                    for ct, schema_info in content_types.items():
                        ref = schema_info.get("schema", {}).get("$ref", "")
                        if ref:
                            endpoint["request_schema"] = ref.split("/")[-1]
                        break

                # Get response schema
                responses = details.get("responses", {})
                for code, resp in responses.items():
                    if code.startswith("2"):
                        resp_content = resp.get("content", {})
                        for ct, schema_info in resp_content.items():
                            ref = schema_info.get("schema", {}).get("$ref", "")
                            if ref:
                                endpoint["response_schema"] = ref.split("/")[-1]
                            break
                        break

                endpoints.append(endpoint)

    return {
        "title": info.get("title", spec_path.stem),
        "version": info.get("version", ""),
        "base_url": (data.get("servers", [{}])[0].get("url", "") if data.get("servers") else ""),
        "endpoints": endpoints,
    }


def _detect_endpoints_from_controllers(repo_root: Path) -> list[dict[str, Any]]:
    """Detect API endpoints from controller attributes in .NET code."""
    import re
    endpoints = []

    for cs_file in repo_root.rglob("*Controller.cs"):
        if _should_ignore(cs_file):
            continue
        try:
            content = cs_file.read_text(errors="replace")
        except (OSError, PermissionError):
            continue

        # Skip test files
        if "Tests" in str(cs_file):
            continue

        service = cs_file.relative_to(repo_root).parts[0]

        # Get route prefix from class
        class_route = ""
        route_match = re.search(r'\[Route\("([^"]+)"\)\]', content)
        if route_match:
            class_route = route_match.group(1)

        # Find HTTP method attributes (flexible whitespace matching)
        for match in re.finditer(
            r'\[(Http(Get|Post|Put|Delete|Patch))(?:\("([^"]*)"\))?\]\s*(?:\[.*?\]\s*)*public\s+(?:async\s+)?\S+\s+(\w+)',
            content, re.DOTALL
        ):
            method = match.group(2).upper()
            route = match.group(3) or ""
            func_name = match.group(4)
            full_path = f"/{class_route}/{route}".replace("//", "/").rstrip("/")
            full_path = re.sub(r'\[controller\]', cs_file.stem.replace('Controller', '').lower(), full_path)
            endpoints.append({
                "service": service,
                "method": method,
                "path": full_path,
                "handler": func_name,
            })

    return endpoints


def discover_apis(repo_root: Path) -> str:
    """Discover all APIs in the repo and return as markdown."""
    lines = ["# API Discovery\n"]

    endpoint_chunks = []

    # Try OpenAPI specs first
    specs = _find_openapi_specs(repo_root)
    if specs:
        lines.append("## OpenAPI Specifications")
        for spec_path in specs:
            parsed = _parse_openapi(spec_path)
            if parsed:
                lines.append(f"\n### {parsed['title']} (v{parsed['version']})")
                if parsed['base_url']:
                    lines.append(f"Base URL: `{parsed['base_url']}`")
                lines.append("")
                for ep in parsed["endpoints"]:
                    req = f" ← {ep['request_schema']}" if ep.get("request_schema") else ""
                    resp = f" → {ep['response_schema']}" if ep.get("response_schema") else ""
                    lines.append(f"- `{ep['method']} {ep['path']}` {ep['summary']}{req}{resp}")
                    endpoint_chunks.append(
                        api_endpoint_chunk(
                            path=str(spec_path.relative_to(repo_root)),
                            method=ep["method"],
                            endpoint=ep["path"],
                            summary=ep.get("summary", ""),
                        )
                    )
                lines.append("")

    # Detect from controllers
    controller_endpoints = _detect_endpoints_from_controllers(repo_root)
    if controller_endpoints:
        lines.append("## Controller Endpoints")
        # Group by service
        by_service: dict[str, list] = {}
        for ep in controller_endpoints:
            svc = ep["service"]
            if svc not in by_service:
                by_service[svc] = []
            by_service[svc].append(ep)

        for svc in sorted(by_service.keys()):
            lines.append(f"\n### {svc}")
            for ep in by_service[svc]:
                lines.append(f"- `{ep['method']} {ep['path']}` → {ep['handler']}()")
                endpoint_chunks.append(
                    api_endpoint_chunk(
                        path=f"{svc}/controller",
                        method=ep["method"],
                        endpoint=ep["path"],
                        summary=f"Handler: {ep['handler']}",
                        service=svc,
                    )
                )
        lines.append("")

    if endpoint_chunks:
        index_chunks(repo_root, "api", endpoint_chunks)

    if len(lines) <= 2:
        return "No APIs discovered. Add OpenAPI specs or check controller annotations."

    return "\n".join(lines)


def search_api(repo_root: Path, query: str) -> str:
    """Search for a specific API endpoint or schema."""
    full_report = discover_apis(repo_root)
    semantic_results = semantic_query(repo_root, "api", query, limit=8)
    if semantic_results:
        lines = [f"# API Search: '{query}'\n", "## Semantic Matches"]
        for result in semantic_results:
            meta = result.get("metadata", {})
            lines.append(f"- `{meta.get('symbol', '')}` ({meta.get('path', '')})")
            lines.append(f"  {result.get('content', '')[:240]}")
        return "\n".join(lines)
    query_lower = query.lower()

    # Filter lines that match
    lines = full_report.splitlines()
    results = []
    current_section = ""
    for line in lines:
        if line.startswith("#"):
            current_section = line
        if query_lower in line.lower():
            if current_section and current_section not in results:
                results.append(current_section)
            results.append(line)

    if not results:
        return f"No API endpoints matching '{query}'. Run full discovery with mnemo_discover_apis."

    return "\n".join(results)
