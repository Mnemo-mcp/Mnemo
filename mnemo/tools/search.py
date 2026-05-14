"""Search & Multi-Repo tools."""

from __future__ import annotations

from pathlib import Path

from ..tool_registry import tool


@tool("mnemo_knowledge",
      "Search the project knowledge base (runbooks, architecture docs, standards, gotchas). Without a query, lists all available knowledge files.",
      properties={"query": {"type": "string", "description": "Search term (optional — omit to list all knowledge files)"}})
def _knowledge(root: Path, args: dict) -> str:
    from ..knowledge import search_knowledge, list_knowledge
    query = args.get("query", "")
    return search_knowledge(root, query) if query else list_knowledge(root)


@tool("mnemo_discover_apis",
      "Discover all API endpoints in the project. Parses OpenAPI/Swagger specs and controller annotations to build a complete API catalog.")
def _discover_apis(root: Path, args: dict) -> str:
    from ..api_discovery import discover_apis
    return discover_apis(root)


@tool("mnemo_search_api",
      "Search for a specific API endpoint, schema, or service in the API catalog.",
      properties={"query": {"type": "string", "description": "Endpoint path, method name, or schema to search for"}},
      required=["query"])
def _search_api(root: Path, args: dict) -> str:
    from ..api_discovery import search_api
    return search_api(root, args.get("query", ""))


@tool("mnemo_links",
      "Show all linked repos in the multi-repo workspace.")
def _links(root: Path, args: dict) -> str:
    from ..workspace import format_links
    return format_links(root)


@tool("mnemo_cross_search",
      "Search across this repo AND all linked repos. Use when looking for code, APIs, or patterns that may live in sibling services.",
      properties={
          "query": {"type": "string", "description": "What to search for across all repos"},
          "namespace": {"type": "string", "description": "Search namespace: code, api, or knowledge (default: code)"},
      },
      required=["query"])
def _cross_search(root: Path, args: dict) -> str:
    from ..workspace import cross_repo_semantic_query
    query = args.get("query", "")
    namespace = args.get("namespace", "code")
    results = cross_repo_semantic_query(root, namespace, query, limit=15)
    if not results:
        return f"No cross-repo results for '{query}'"
    lines = [f"# Cross-Repo Search: '{query}'\n"]
    for r in results:
        meta = r.get("metadata", {})
        lines.append(f"- **[{r.get('repo', '?')}]** `{meta.get('path', '')}` :: `{meta.get('symbol', '')}`")
        if r.get("content"):
            lines.append(f"  {r['content'][:200]}")
    return "\n".join(lines)


@tool("mnemo_cross_impact",
      "Cross-repo impact analysis — find what breaks across ALL linked repos if you change a service, file, or API.",
      properties={"query": {"type": "string", "description": "Service, file, or API to analyze impact for"}},
      required=["query"])
def _cross_impact(root: Path, args: dict) -> str:
    from ..workspace import cross_repo_impact
    return cross_repo_impact(root, args.get("query", ""))
