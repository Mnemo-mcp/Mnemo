"""Team & Operations tools."""

from __future__ import annotations

from pathlib import Path

from ..tool_registry import tool


@tool("mnemo_record",
      "Store or search engineering records (errors, incidents, reviews, corrections).",
      properties={
          "type": {"type": "string", "description": "error|incident|review|correction"},
          "action": {"type": "string", "description": "add|search|list"},
          "query": {"type": "string", "description": "Search query (for search action)"},
          "error": {"type": "string", "description": "Error message (for error/add)"},
          "cause": {"type": "string", "description": "Root cause (for error/add)"},
          "fix": {"type": "string", "description": "How it was fixed (for error/add, incident/add)"},
          "file": {"type": "string"},
          "tags": {"type": "array", "items": {"type": "string"}},
          "title": {"type": "string", "description": "Incident title (for incident/add)"},
          "what_happened": {"type": "string"},
          "root_cause": {"type": "string"},
          "prevention": {"type": "string"},
          "severity": {"type": "string", "description": "low, medium, high, critical"},
          "services": {"type": "array", "items": {"type": "string"}},
          "summary": {"type": "string", "description": "Review summary (for review/add)"},
          "files": {"type": "array", "items": {"type": "string"}},
          "feedback": {"type": "string"},
          "outcome": {"type": "string", "description": "approved, rejected, or changes_requested"},
          "suggestion": {"type": "string", "description": "AI suggestion (for correction/add)"},
          "correction": {"type": "string", "description": "User correction (for correction/add)"},
          "context": {"type": "string"},
          "limit": {"type": "integer"},
          "offset": {"type": "integer"},
      },
      required=["type", "action"])
def _record(root: Path, args: dict) -> str:
    record_type = args.get("type", "")
    action = args.get("action", "list")

    if record_type == "error":
        if action == "add":
            from ..errors import add_error
            entry = add_error(root, args.get("error", ""), args.get("cause", ""),
                              args.get("fix", ""), args.get("file", ""), args.get("tags", []))
            return f"Error #{entry['id']} stored."
        from ..errors import search_errors
        return search_errors(root, args.get("query", ""))

    elif record_type == "incident":
        if action == "add":
            from ..incidents import add_incident
            entry = add_incident(root, args.get("title", ""), args.get("what_happened", ""),
                                 args.get("root_cause", ""), args.get("fix", ""),
                                 args.get("prevention", ""), args.get("severity", "medium"),
                                 args.get("services", []))
            return f"Incident #{entry['id']} recorded."
        from ..incidents import search_incidents, format_incidents
        query = args.get("query", "")
        if query:
            return search_incidents(root, query)
        return format_incidents(root, limit=int(args.get("limit", 20)), offset=int(args.get("offset", 0)))

    elif record_type == "review":
        if action == "add":
            from ..storage import Collections, get_storage
            storage = get_storage(root)
            reviews = storage.read_collection(Collections.REVIEWS)
            if not isinstance(reviews, list):
                reviews = []
            import time
            next_id = max((r.get("id", 0) for r in reviews), default=0) + 1
            entry = {"id": next_id, "timestamp": time.time(), "summary": args.get("summary", ""),
                     "files": args.get("files", []), "feedback": args.get("feedback", ""),
                     "outcome": args.get("outcome", "approved")}
            reviews.append(entry)
            storage.write_collection(Collections.REVIEWS, reviews[-100:])
            return f"Review #{entry['id']} stored."
        from ..storage import Collections, get_storage
        storage = get_storage(root)
        reviews = storage.read_collection(Collections.REVIEWS)
        if not isinstance(reviews, list) or not reviews:
            return "No code review history stored."
        limit = int(args.get("limit", 20))
        offset = int(args.get("offset", 0))
        total = len(reviews)
        page = reviews[offset:offset + limit]
        lines = [f"# Code Review History ({total} total)\n"]
        for review in page:
            status = f"[{review['outcome']}]" if review.get("outcome") else ""
            lines.append(f"- {review['summary']} {status}")
            if review.get("feedback"):
                lines.append(f"  Feedback: {review['feedback']}")
        if total > offset + limit:
            lines.append(f"\n*Showing {len(page)} of {total}. Use offset={offset + limit} for more.*")
        return "\n".join(lines)

    elif record_type == "correction":
        if action == "add":
            from ..corrections import add_correction
            entry = add_correction(root, args.get("suggestion", ""), args.get("correction", ""),
                                   args.get("context", ""), args.get("file", ""))
            return f"Correction #{entry['id']} stored."
        from ..corrections import get_corrections
        return get_corrections(root, args.get("query", ""),
                               limit=int(args.get("limit", 20)), offset=int(args.get("offset", 0)))

    return f"Unknown record type: {record_type}. Use: error, incident, review, correction"





@tool("mnemo_dependencies",
      "Show the full service dependency graph — which service depends on which.")
def _dependencies(root: Path, args: dict) -> str:
    from ..engine.db import open_db, get_db_path
    if not get_db_path(root).exists():
        return "No graph. Run `mnemo init`."
    _, conn = open_db(root)
    lines = ["# Service Dependencies\n"]
    r = conn.execute("MATCH (a:File)-[:IMPORTS]->(b:File) RETURN a.path, b.path")
    deps: dict[str, set] = {}
    while r.has_next():
        row = r.get_next()
        src = row[0].split("/")[0]
        tgt = row[1].split("/")[0]
        if src != tgt:
            deps.setdefault(src, set()).add(tgt)
    for svc, targets in sorted(deps.items()):
        lines.append(f"- **{svc}** → {', '.join(sorted(targets))}")
    return "\n".join(lines) if len(lines) > 1 else "No cross-service dependencies found."


@tool("mnemo_impact_imports",
      "File-level impact — find which files import/depend on a given file.",
      properties={"query": {"type": "string", "description": "File name or path fragment to analyze"}},
      required=["query"])
def _impact(root: Path, args: dict) -> str:
    from ..engine.db import open_db, get_db_path
    if not get_db_path(root).exists():
        return "No graph. Run `mnemo init`."
    _, conn = open_db(root)
    query = args.get("query", "")
    lines = [f"# Impact Analysis: {query}\n"]
    # Files that import the queried file/service
    r = conn.execute("MATCH (a:File)-[:IMPORTS]->(b:File) WHERE b.path CONTAINS $query RETURN a.path", {"query": query})
    dependents = []
    while r.has_next():
        dependents.append(r.get_next()[0])
    if dependents:
        lines.append(f"## {len(dependents)} files depend on `{query}`:")
        for d in dependents[:20]:
            lines.append(f"- `{d}`")
    else:
        lines.append("No dependents found.")
    return "\n".join(lines)


@tool("mnemo_onboarding",
      "Generate a complete project onboarding guide for new team members.")
def _onboarding(root: Path, args: dict) -> str:
    from ..onboarding import generate_onboarding
    return generate_onboarding(root)


@tool("mnemo_tests",
      "Show which tests cover a file, or get overall test coverage summary. Use when modifying code to know what tests to run.",
      properties={"query": {"type": "string", "description": "File name to find tests for (omit for coverage summary)"}})
def _tests(root: Path, args: dict) -> str:
    try:
        from ..test_intel import get_tests_for_file, get_coverage_summary
    except ImportError:
        return "Test intelligence module not available."
    query = args.get("query", "")
    return get_tests_for_file(root, query) if query else get_coverage_summary(root)


@tool("mnemo_team",
      "Show team expertise map — who knows what based on git history.",
      properties={"query": {"type": "string", "description": "Service or area to find experts for (omit for full map)"}})
def _team(root: Path, args: dict) -> str:
    from ..team_graph import get_experts
    return get_experts(root, args.get("query", ""))


@tool("mnemo_who_touched",
      "Find who last modified a specific file.",
      properties={"query": {"type": "string", "description": "File path or name"}},
      required=["query"])
def _who_touched(root: Path, args: dict) -> str:
    from ..team_graph import who_last_touched
    return who_last_touched(root, args.get("query", ""))



