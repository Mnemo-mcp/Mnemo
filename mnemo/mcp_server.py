"""MCP Server – Exposes Mnemo tools to Amazon Q."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .init import init
from .config import MNEMO_DIR
from .tool_registry import get_handler as _registry_handler, all_tools as _all_registry_tools
from . import __version__


def _find_repo_root(start: Path | None = None) -> Path | None:
    """Walk up from start to find a directory containing .mnemo/."""
    current = start or Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / MNEMO_DIR).exists():
            return parent
    return None


_GRAPH_TOOLS = frozenset({
    "mnemo_lookup", "mnemo_graph", "mnemo_impact", "mnemo_symbol",
    "mnemo_search", "mnemo_communities", "mnemo_map",
})


def _validate_required(arguments: dict, required: list[str]) -> str | None:
    """Return error message if required fields are missing, else None."""
    missing = [f for f in required if f not in arguments]
    if missing:
        return f"Missing required fields: {', '.join(missing)}"
    return None


# --- Input sanitization ---
_MAX_STRING_LENGTH = 100_000
_MAX_ARRAY_LENGTH = 500


def _sanitize_arguments(arguments: dict, schema: dict | None) -> str | None:
    """Validate argument types and enforce limits. Returns error message or None."""
    if not schema:
        return None
    properties = schema.get("inputSchema", {}).get("properties", {})
    for key, value in arguments.items():
        if key == "repo_path":
            continue
        prop_schema = properties.get(key, {})
        expected_type = prop_schema.get("type")
        # Type validation
        if expected_type == "string" and not isinstance(value, str):
            arguments[key] = str(value) if value is not None else ""
        elif expected_type == "integer" and not isinstance(value, int):
            try:
                arguments[key] = int(value)
            except (ValueError, TypeError):
                return f"Field '{key}' must be an integer"
        elif expected_type == "boolean" and not isinstance(value, bool):
            arguments[key] = bool(value)
        elif expected_type == "array" and not isinstance(value, list):
            return f"Field '{key}' must be an array"
        # Length limits
        if isinstance(value, str) and len(value) > _MAX_STRING_LENGTH:
            return f"Field '{key}' exceeds maximum length ({_MAX_STRING_LENGTH} chars)"
        if isinstance(value, list) and len(value) > _MAX_ARRAY_LENGTH:
            return f"Field '{key}' exceeds maximum array length ({_MAX_ARRAY_LENGTH} items)"
    # Path traversal check for file-related arguments
    for key in ("file", "query", "repo_path"):
        val = arguments.get(key, "")
        if isinstance(val, str) and ".." in val.split("/"):
            # Allow .. only if it resolves within a reasonable path
            try:
                resolved = Path(val).resolve()
                if str(resolved).startswith("/etc") or str(resolved).startswith("/proc"):
                    return f"Field '{key}' contains disallowed path"
            except (ValueError, OSError):
                return f"Field '{key}' contains invalid path"
    return None


def handle_tool_call(tool_name: str, arguments: dict) -> dict:
    """Route MCP tool calls with input validation and sanitization."""
    # Validate required fields from schema (O(1) lookup via registry)
    from .tool_registry import get_schema as _get_schema
    schema = _get_schema(tool_name)
    if schema:
        required = schema.get("inputSchema", {}).get("required", [])
        required = [r for r in required if r != "repo_path"]
        err = _validate_required(arguments, required)
        if err:
            return {"content": [{"type": "text", "text": err}], "isError": True}
        # Sanitize inputs
        err = _sanitize_arguments(arguments, schema)
        if err:
            return {"content": [{"type": "text", "text": err}], "isError": True}
    elif tool_name == "mnemo_init":
        required = [r for r in _INIT_TOOL["inputSchema"].get("required", []) if r != "repo_path"]
        err = _validate_required(arguments, required)
        if err:
            return {"content": [{"type": "text", "text": err}], "isError": True}

    # Auto-detect repo root, fallback to explicit path
    repo_path = arguments.get("repo_path")
    if repo_path:
        repo_root = Path(repo_path).resolve()
    else:
        repo_root = _find_repo_root()

    # mnemo_init is special — doesn't require existing .mnemo/
    if tool_name == "mnemo_init":
        target = Path(repo_path).resolve() if repo_path else Path.cwd()
        try:
            msg = init(target, client=arguments.get("client", "amazonq"))
        except ValueError as exc:
            return {"content": [{"type": "text", "text": str(exc)}], "isError": True}
        return {"content": [{"type": "text", "text": msg}]}

    if not repo_root:
        return {"content": [{"type": "text", "text": "No .mnemo/ found. Run `mnemo init` in your repo first."}], "isError": True}

    # Dispatch via registry
    handler = _registry_handler(tool_name)
    if handler:
        try:
            # Ensure graph is fresh for graph-reading tools
            if tool_name in _GRAPH_TOOLS:
                from .engine.freshness import ensure_graph_fresh
                ensure_graph_fresh(repo_root)
            result = handler(repo_root, arguments)
            return {"content": [{"type": "text", "text": result}]}
        except Exception as exc:
            return {"content": [{"type": "text", "text": f"Error: {exc}"}], "isError": True}

    return {"content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}], "isError": True}


# mnemo_init is special (no .mnemo/ required), so it stays here.
_INIT_TOOL = {
    "name": "mnemo_init",
    "description": "Initialize Mnemo in a repository. Creates .mnemo/ folder, generates repo map, and bootstraps memory.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Path to the repository root"},
            "client": {"type": "string", "description": "AI client to configure: amazonq, cursor, claude-code, kiro, copilot, generic, or all"},
        },
        "required": ["repo_path"],
    },
}

TOOLS = [_INIT_TOOL] + _all_registry_tools()


def run_stdio():
    """Run as MCP server over stdio (JSON-RPC)."""
    for line in sys.stdin:
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = request.get("method")
        req_id = request.get("id")

        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "mnemo", "version": __version__},
                },
            }
        elif method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": TOOLS},
            }
        elif method == "tools/call":
            params = request.get("params", {})
            result = handle_tool_call(params["name"], params.get("arguments", {}))
            response = {"jsonrpc": "2.0", "id": req_id, "result": result}
        elif method == "notifications/initialized":
            continue
        else:
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown method: {method}"},
            }

        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    run_stdio()
