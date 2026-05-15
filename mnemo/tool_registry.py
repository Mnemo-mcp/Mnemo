"""Tool registry for MCP server — decouples tool definitions from dispatch."""

from __future__ import annotations

from typing import Callable

from .utils.logger import get_logger

logger = get_logger("tool_registry")

# Registry: tool_name -> (handler_fn, schema_dict)
_REGISTRY: dict[str, tuple[Callable, dict]] = {}

# Shared schema fragment — use in all tool inputSchema properties
REPO_PATH_PROP = {"type": "string", "description": "Path to the repository root (auto-detected if omitted)"}


def register(name: str, handler: Callable, schema: dict) -> None:
    """Register a tool with its handler and input schema."""
    _REGISTRY[name] = (handler, schema)


def tool(name: str, description: str, properties: dict | None = None, required: list[str] | None = None):
    """Decorator for tool registration. Automatically includes repo_path property.

    Usage:
        @tool("mnemo_map", "Regenerate the repo map.")
        def _map(root: Path, args: dict) -> str:
            ...

        @tool("mnemo_lookup", "Look up code structure.", properties={"query": {...}}, required=["query"])
        def _lookup(root: Path, args: dict) -> str:
            ...
    """
    def decorator(fn: Callable) -> Callable:
        props = {"repo_path": REPO_PATH_PROP}
        if properties:
            props.update(properties)
        schema = {
            "description": description,
            "inputSchema": {"type": "object", "properties": props},
        }
        if required:
            schema["inputSchema"]["required"] = required
        _REGISTRY[name] = (fn, schema)
        return fn
    return decorator


# Core tool set — only these are exposed to agents
_CORE_TOOLS = {
    "mnemo_recall", "mnemo_remember", "mnemo_decide", "mnemo_search",
    "mnemo_plan", "mnemo_graph", "mnemo_lookup", "mnemo_audit",
    "mnemo_record", "mnemo_generate", "mnemo_map", "mnemo_context",
    "mnemo_forget", "mnemo_ask", "mnemo_lesson",
}


def all_tools() -> list[dict]:
    """Return only core tools in MCP tools/list format (15 tools)."""
    _ensure_loaded()
    return [
        {"name": name, "description": schema.get("description", ""), "inputSchema": schema.get("inputSchema", {})}
        for name, (_, schema) in _REGISTRY.items()
        if name in _CORE_TOOLS
    ]


def registered_names() -> list[str]:
    """Return core tool names exposed to agents."""
    _ensure_loaded()
    return [n for n in _REGISTRY.keys() if n in _CORE_TOOLS]


def all_registered_names() -> list[str]:
    """Return ALL registered tool names (including internal/aliases)."""
    _ensure_loaded()
    return list(_REGISTRY.keys())


_tools_loaded = False


def _ensure_loaded():
    """Lazily import and register all tool modules on first access."""
    global _tools_loaded
    if not _tools_loaded:
        _tools_loaded = True
        from . import tools  # noqa: F401
        _ensure_hooks()


def get_handler(name: str) -> Callable | None:
    """Get handler function for a tool name."""
    _ensure_loaded()
    entry = _REGISTRY.get(name)
    return entry[0] if entry else None


def get_schema(name: str) -> dict | None:
    """Get input schema for a tool name."""
    _ensure_loaded()
    entry = _REGISTRY.get(name)
    return entry[1] if entry else None





_hooks_wired = False


def _ensure_hooks():
    """Wire memory mutation hooks (deferred until first tool access)."""
    global _hooks_wired
    if _hooks_wired:
        return
    _hooks_wired = True
    from .memory import register_on_mutate
    from .init import refresh_context_files
    register_on_mutate(refresh_context_files)
