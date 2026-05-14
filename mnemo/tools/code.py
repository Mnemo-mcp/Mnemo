"""Code Understanding tools."""

from __future__ import annotations

from pathlib import Path

from ..tool_registry import tool


@tool("mnemo_lookup",
      "Look up detailed code structure for a specific file or folder. Returns full method signatures, imports, and class details. Use this when you need to understand a specific part of the codebase in depth.",
      properties={"query": {"type": "string", "description": "File name, folder name, or path fragment to search for (e.g. 'AuthService', 'Controllers', 'UserController.cs')"}},
      required=["query"])
def _lookup(root: Path, args: dict) -> str:
    from ..memory import lookup
    return lookup(root, args.get("query", ""))


@tool("mnemo_map",
      "Regenerate the repo map. Use this after significant code changes to keep the structural map up to date.")
def _map(root: Path, args: dict) -> str:
    from ..repo_map import save_repo_map
    return f"Repo map regenerated: {save_repo_map(root)}"


@tool("mnemo_intelligence",
      "Generate a code intelligence report: architecture graph (service-to-service calls), dependency map, detected patterns and conventions, code ownership.")
def _intelligence(root: Path, args: dict) -> str:
    from ..intelligence import generate_intelligence
    return generate_intelligence(root)


@tool("mnemo_similar",
      "Find similar implementations in the codebase. Use this when implementing something new to find existing patterns to follow (e.g. 'Handler' finds all handler implementations).",
      properties={"query": {"type": "string", "description": "Pattern name to search for (e.g. 'Handler', 'Service', 'Controller')"}},
      required=["query"])
def _similar(root: Path, args: dict) -> str:
    from ..intelligence import find_similar
    query = args.get("query", "")
    results = find_similar(root, query)
    if not results:
        return f"No similar implementations for '{query}'"
    lines = [f"# Similar to '{query}'\n"]
    for r in results:
        lines.append(f"- **{r['file']}** — `{r['class']}`")
        if r.get("content"):
            lines.append(f"  ```\n  {r['content']}\n  ```")
    return "\n".join(lines)


@tool("mnemo_context_for_task",
      "Return context relevant to the active mnemo_task using semantic retrieval with fallback behavior.",
      properties={"query": {"type": "string", "description": "Optional extra focus query (e.g. endpoint, module, feature)"}})
def _context_for_task(root: Path, args: dict) -> str:
    from ..intelligence import context_for_active_task
    return context_for_active_task(root, args.get("query", ""))
