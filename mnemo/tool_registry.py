"""Tool registry for MCP server — decouples tool definitions from dispatch."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

# Registry: tool_name -> (handler_fn, schema_dict)
_REGISTRY: dict[str, tuple[Callable, dict]] = {}


def register(name: str, handler: Callable, schema: dict) -> None:
    """Register a tool with its handler and input schema."""
    _REGISTRY[name] = (handler, schema)


def get_handler(name: str) -> Callable | None:
    """Get handler function for a tool name."""
    entry = _REGISTRY.get(name)
    return entry[0] if entry else None


def get_schema(name: str) -> dict | None:
    """Get input schema for a tool name."""
    entry = _REGISTRY.get(name)
    return entry[1] if entry else None


def all_tools() -> list[dict]:
    """Return all registered tools in MCP tools/list format."""
    return [
        {"name": name, "description": schema.get("description", ""), "inputSchema": schema.get("inputSchema", {})}
        for name, (_, schema) in _REGISTRY.items()
    ]


def registered_names() -> list[str]:
    """Return all registered tool names."""
    return list(_REGISTRY.keys())


# ---------------------------------------------------------------------------
# Handler registrations
# ---------------------------------------------------------------------------

def _register_all() -> None:
    """Register all built-in tool handlers."""
    import sys
    try:
        from .memory import add_memory, add_decision, save_context, recall, lookup, search_memory, forget_memory
        from .repo_map import save_repo_map
        from .intelligence import generate_intelligence, find_similar, context_for_active_task
        from .workspace import cross_repo_semantic_query, cross_repo_impact, format_links
        from .knowledge import search_knowledge, list_knowledge
        from .api_discovery import discover_apis, search_api
        from .code_review import add_review, format_reviews
        from .errors import add_error, search_errors
        from .dependency_graph import format_graph, impact_analysis
        from .onboarding import generate_onboarding
        from .sprint import set_current_task, complete_task, get_current_task
        from .test_intel import get_tests_for_file, get_coverage_summary
        from .health import calculate_health
        from .team_graph import get_experts, who_last_touched
        from .incidents import add_incident, search_incidents, format_incidents
        from .commit_gen import generate_commit_message
        from .pr_gen import generate_pr_description
        from .dead_code import detect_dead_code
        from .security import add_security_pattern, check_security
        from .breaking import detect_breaking_changes, save_baseline
        from .regressions import add_regression, check_regressions, list_regressions
        from .drift import detect_drift
        from .hooks import install_hooks, run_check
        from .corrections import add_correction, get_corrections
        from .velocity import calculate_velocity
        from .graph.query import query_graph
        from .plan import handle_plan
    except ImportError as exc:
        print(f"[mnemo] Failed to load tool modules: {exc}", file=sys.stderr)
        return

    # --- Memory & Context ---

    def _recall(root: Path, args: dict) -> str:
        data = recall(root)
        return data or "Memory is empty. Run mnemo_init first."

    def _lookup(root: Path, args: dict) -> str:
        return lookup(root, args.get("query", ""))

    def _remember(root: Path, args: dict) -> str:
        entry = add_memory(root, args["content"], args.get("category", "general"))
        result = f"Stored memory #{entry['id']}: {entry['content']}"
        # Auto-detect if this looks like a plan
        from .plan import auto_create_plan_from_text
        plan_result = auto_create_plan_from_text(root, args["content"], source="memory")
        if plan_result:
            result += f"\n\n{plan_result}"
        return result

    def _forget(root: Path, args: dict) -> str:
        return forget_memory(root, int(args.get("memory_id", 0)))

    def _search_mem(root: Path, args: dict) -> str:
        return search_memory(root, args.get("query", ""), deep=args.get("deep", False))

    def _decide(root: Path, args: dict) -> str:
        entry = add_decision(root, args["decision"], args.get("reasoning", ""))
        result = f"Decision #{entry['id']} recorded: {entry['decision']}"
        # Auto-detect if this decision implies trackable work
        from .plan import auto_create_plan_from_text
        combined = f"{args['decision']}\n{args.get('reasoning', '')}"
        plan_result = auto_create_plan_from_text(root, combined, source="decision")
        if plan_result:
            result += f"\n\n{plan_result}"
        return result

    def _context(root: Path, args: dict) -> str:
        save_context(root, args.get("context", {}))
        return "Context updated."

    def _map(root: Path, args: dict) -> str:
        return f"Repo map regenerated: {save_repo_map(root)}"

    # --- Code Intelligence ---

    def _intelligence(root: Path, args: dict) -> str:
        return generate_intelligence(root)

    def _similar(root: Path, args: dict) -> str:
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

    def _context_for_task(root: Path, args: dict) -> str:
        return context_for_active_task(root, args.get("query", ""))

    # --- Knowledge & APIs ---

    def _knowledge(root: Path, args: dict) -> str:
        query = args.get("query", "")
        return search_knowledge(root, query) if query else list_knowledge(root)

    def _discover_apis(root: Path, args: dict) -> str:
        return discover_apis(root)

    def _search_api(root: Path, args: dict) -> str:
        return search_api(root, args.get("query", ""))

    # --- Code Review ---

    def _add_review(root: Path, args: dict) -> str:
        entry = add_review(root, args["summary"], args.get("files", []),
                           args.get("feedback", ""), args.get("outcome", "approved"))
        return f"Review #{entry['id']} stored."

    def _reviews(root: Path, args: dict) -> str:
        return format_reviews(root, limit=int(args.get("limit", 20)), offset=int(args.get("offset", 0)))

    # --- Error Memory ---

    def _add_error(root: Path, args: dict) -> str:
        entry = add_error(root, args["error"], args["cause"], args["fix"],
                          args.get("file", ""), args.get("tags", []))
        return f"Error #{entry['id']} stored."

    def _search_errors(root: Path, args: dict) -> str:
        return search_errors(root, args.get("query", ""))

    # --- Dependency Graph ---

    def _dependencies(root: Path, args: dict) -> str:
        return format_graph(root)

    def _impact(root: Path, args: dict) -> str:
        return impact_analysis(root, args.get("query", ""))

    # --- Onboarding ---

    def _onboarding(root: Path, args: dict) -> str:
        return generate_onboarding(root)

    # --- Sprint/Task ---

    def _task(root: Path, args: dict) -> str:
        task_id = args.get("task_id", "")
        if not task_id:
            return get_current_task(root)
        set_current_task(root, task_id, args.get("description", ""),
                         args.get("files", []), args.get("notes", ""))
        return f"Task {task_id} set as active."

    def _task_done(root: Path, args: dict) -> str:
        return complete_task(root, args.get("task_id", ""), args.get("summary", ""))

    # --- Test Intelligence ---

    def _tests(root: Path, args: dict) -> str:
        query = args.get("query", "")
        return get_tests_for_file(root, query) if query else get_coverage_summary(root)

    # --- Code Health ---

    def _health(root: Path, args: dict) -> str:
        return calculate_health(root)

    # --- Team Graph ---

    def _team(root: Path, args: dict) -> str:
        return get_experts(root, args.get("query", ""))

    def _who_touched(root: Path, args: dict) -> str:
        return who_last_touched(root, args.get("query", ""))

    # --- Incidents ---

    def _add_incident(root: Path, args: dict) -> str:
        entry = add_incident(root, args["title"], args["what_happened"],
                             args["root_cause"], args["fix"],
                             args.get("prevention", ""), args.get("severity", "medium"),
                             args.get("services", []))
        return f"Incident #{entry['id']} recorded."

    def _incidents(root: Path, args: dict) -> str:
        query = args.get("query", "")
        if query:
            return search_incidents(root, query)
        return format_incidents(root, limit=int(args.get("limit", 20)), offset=int(args.get("offset", 0)))

    # --- Commit & PR ---

    def _commit_message(root: Path, args: dict) -> str:
        return generate_commit_message(root)

    def _pr_description(root: Path, args: dict) -> str:
        return generate_pr_description(root)

    # --- Dead Code ---

    def _dead_code(root: Path, args: dict) -> str:
        return detect_dead_code(root)

    # --- Security ---

    def _add_security_pattern(root: Path, args: dict) -> str:
        entry = add_security_pattern(root, args["name"], args["regex"],
                                     args.get("severity", "medium"), args.get("description", ""))
        return f"Security pattern #{entry['id']} added: {entry['name']}"

    def _check_security(root: Path, args: dict) -> str:
        return check_security(root, args.get("file", ""))

    # --- Breaking Changes ---

    def _breaking_changes(root: Path, args: dict) -> str:
        if args.get("action") == "baseline":
            return save_baseline(root)
        return detect_breaking_changes(root)

    # --- Regressions ---

    def _add_regression(root: Path, args: dict) -> str:
        entry = add_regression(root, args["file"], args["bug"], args["fix"], args.get("test", ""))
        return f"Regression #{entry['id']} recorded for {entry['file']}"

    def _check_regressions(root: Path, args: dict) -> str:
        file = args.get("file", "")
        return check_regressions(root, file) if file else list_regressions(root)

    # --- Architecture Drift ---

    def _drift(root: Path, args: dict) -> str:
        return detect_drift(root)

    # --- Git Hooks ---

    def _hooks_install(root: Path, args: dict) -> str:
        return install_hooks(root)

    def _check(root: Path, args: dict) -> str:
        return run_check(root)

    # --- Corrections ---

    def _add_correction(root: Path, args: dict) -> str:
        entry = add_correction(root, args["suggestion"], args["correction"],
                               args.get("context", ""), args.get("file", ""))
        return f"Correction #{entry['id']} stored."

    def _corrections(root: Path, args: dict) -> str:
        return get_corrections(root, args.get("query", ""),
                               limit=int(args.get("limit", 20)), offset=int(args.get("offset", 0)))

    # --- Velocity ---

    def _velocity(root: Path, args: dict) -> str:
        return calculate_velocity(root)

    # --- Knowledge Graph ---

    def _graph_query(root: Path, args: dict) -> str:
        action = args.get("action", "stats")
        return query_graph(
            root, action,
            node=args.get("node", ""),
            target=args.get("target", ""),
            edge_type=args.get("edge_type"),
            edge_types=args.get("edge_type", "").split(",") if args.get("edge_type") else None,
            depth=int(args.get("depth", 2)),
            direction=args.get("direction", "both"),
            type=args.get("type"),
            name=args.get("name"),
        )

    # --- Plan Mode ---

    def _plan(root: Path, args: dict) -> str:
        return handle_plan(root, args)

    # --- Multi-Repo ---

    def _links(root: Path, args: dict) -> str:
        return format_links(root)

    def _cross_search(root: Path, args: dict) -> str:
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

    def _cross_impact(root: Path, args: dict) -> str:
        return cross_repo_impact(root, args.get("query", ""))

    # --- Schemas ---
    _rp = {"type": "string", "description": "Path to the repository root (auto-detected if omitted)"}

    _schemas = {
        "mnemo_recall": {
            "description": "Recall all stored memory, decisions, context, and repo map. YOU MUST call this at the START of every new chat to load project context before answering any questions.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp}},
        },
        "mnemo_lookup": {
            "description": "Look up detailed code structure for a specific file or folder. Returns full method signatures, imports, and class details. Use this when you need to understand a specific part of the codebase in depth.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "query": {"type": "string", "description": "File name, folder name, or path fragment to search for (e.g. 'AuthService', 'Controllers', 'UserController.cs')"}}, "required": ["query"]},
        },
        "mnemo_remember": {
            "description": "Store important information in persistent memory. Use this to save context, user preferences, patterns, or anything that should be remembered across chat sessions.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "content": {"type": "string", "description": "The information to remember"}, "category": {"type": "string", "description": "Category: general, architecture, preference, pattern, bug, todo"}}, "required": ["content"]},
        },
        "mnemo_forget": {
            "description": "Delete a specific memory entry by ID. Use when a memory is wrong or outdated.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "memory_id": {"type": "integer", "description": "ID of the memory to delete"}}, "required": ["memory_id"]},
        },
        "mnemo_search_memory": {
            "description": "Search stored memories semantically. Use when mnemo_recall does not have enough context. Auto-detects relevant category from your query.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "query": {"type": "string", "description": "What to search for in memory (e.g. auth token bug, caching decision)"}, "deep": {"type": "boolean", "description": "Set true for more results (15 instead of 7)"}}, "required": ["query"]},
        },
        "mnemo_decide": {
            "description": "Record an architectural or design decision with reasoning. Use this whenever a significant technical choice is made.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "decision": {"type": "string", "description": "The decision that was made"}, "reasoning": {"type": "string", "description": "Why this decision was made"}}, "required": ["decision"]},
        },
        "mnemo_context": {
            "description": "Save or update project context (tech stack, conventions, preferences). Merges with existing context.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "context": {"type": "object", "description": "Key-value pairs of project context to store"}}, "required": ["context"]},
        },
        "mnemo_map": {
            "description": "Regenerate the repo map. Use this after significant code changes to keep the structural map up to date.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp}},
        },
        "mnemo_intelligence": {
            "description": "Generate a code intelligence report: architecture graph (service-to-service calls), dependency map, detected patterns and conventions, code ownership.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp}},
        },
        "mnemo_similar": {
            "description": "Find similar implementations in the codebase. Use this when implementing something new to find existing patterns to follow (e.g. 'Handler' finds all handler implementations).",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "query": {"type": "string", "description": "Pattern name to search for (e.g. 'Handler', 'Service', 'Controller')"}}, "required": ["query"]},
        },
        "mnemo_context_for_task": {
            "description": "Return context relevant to the active mnemo_task using semantic retrieval with fallback behavior.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "query": {"type": "string", "description": "Optional extra focus query (e.g. endpoint, module, feature)"}}},
        },
        "mnemo_knowledge": {
            "description": "Search the project knowledge base (runbooks, architecture docs, standards, gotchas). Without a query, lists all available knowledge files.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "query": {"type": "string", "description": "Search term (optional — omit to list all knowledge files)"}}},
        },
        "mnemo_discover_apis": {
            "description": "Discover all API endpoints in the project. Parses OpenAPI/Swagger specs and controller annotations to build a complete API catalog.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp}},
        },
        "mnemo_search_api": {
            "description": "Search for a specific API endpoint, schema, or service in the API catalog.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "query": {"type": "string", "description": "Endpoint path, method name, or schema to search for"}}, "required": ["query"]},
        },
        "mnemo_add_review": {
            "description": "Store a code review summary with feedback and outcome.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "summary": {"type": "string", "description": "What was reviewed"}, "files": {"type": "array", "items": {"type": "string"}, "description": "Files involved"}, "feedback": {"type": "string", "description": "Review feedback"}, "outcome": {"type": "string", "description": "approved, rejected, or changes_requested"}}, "required": ["summary"]},
        },
        "mnemo_reviews": {
            "description": "Show code review history.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "limit": {"type": "integer", "description": "Max results (default 20)"}, "offset": {"type": "integer", "description": "Skip first N results (default 0)"}}},
        },
        "mnemo_add_error": {
            "description": "Store an error → cause → fix mapping for future reference.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "error": {"type": "string", "description": "The error message or symptom"}, "cause": {"type": "string", "description": "Root cause"}, "fix": {"type": "string", "description": "How it was fixed"}, "file": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}}, "required": ["error", "cause", "fix"]},
        },
        "mnemo_search_errors": {
            "description": "Search known errors for a matching issue. Use when user hits an error to check if it's been seen before.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "query": {"type": "string", "description": "Error message or keyword"}}, "required": ["query"]},
        },
        "mnemo_dependencies": {
            "description": "Show the full service dependency graph — which service depends on which.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp}},
        },
        "mnemo_impact": {
            "description": "Impact analysis — what breaks if you change a specific service or file.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "query": {"type": "string", "description": "Service or file name to analyze"}}, "required": ["query"]},
        },
        "mnemo_onboarding": {
            "description": "Generate a complete project onboarding guide for new team members.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp}},
        },
        "mnemo_task": {
            "description": "Set or get the current task/ticket being worked on. Without task_id, shows active tasks.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "task_id": {"type": "string", "description": "Ticket ID (e.g. JIRA-123)"}, "description": {"type": "string"}, "files": {"type": "array", "items": {"type": "string"}}, "notes": {"type": "string"}}},
        },
        "mnemo_task_done": {
            "description": "Mark a task as completed.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "task_id": {"type": "string"}, "summary": {"type": "string"}}, "required": ["task_id"]},
        },
        "mnemo_tests": {
            "description": "Show which tests cover a file, or get overall test coverage summary. Use when modifying code to know what tests to run.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "query": {"type": "string", "description": "File name to find tests for (omit for coverage summary)"}}},
        },
        "mnemo_health": {
            "description": "Code health report — complexity hotspots, large files, potential god classes.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp}},
        },
        "mnemo_team": {
            "description": "Show team expertise map — who knows what based on git history.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "query": {"type": "string", "description": "Service or area to find experts for (omit for full map)"}}},
        },
        "mnemo_who_touched": {
            "description": "Find who last modified a specific file.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "query": {"type": "string", "description": "File path or name"}}, "required": ["query"]},
        },
        "mnemo_add_incident": {
            "description": "Record a production incident with root cause and fix.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "title": {"type": "string"}, "what_happened": {"type": "string"}, "root_cause": {"type": "string"}, "fix": {"type": "string"}, "prevention": {"type": "string"}, "severity": {"type": "string", "description": "low, medium, high, critical"}, "services": {"type": "array", "items": {"type": "string"}}}, "required": ["title", "what_happened", "root_cause", "fix"]},
        },
        "mnemo_incidents": {
            "description": "Search or list production incidents.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "query": {"type": "string", "description": "Search term (omit to list all)"}, "limit": {"type": "integer", "description": "Max results (default 20)"}, "offset": {"type": "integer", "description": "Skip first N results (default 0)"}}},
        },
        "mnemo_commit_message": {
            "description": "Generate a commit message from staged git changes and recent memory context. Returns a conventional commit format message.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp}},
        },
        "mnemo_pr_description": {
            "description": "Generate a PR description from branch diff, active task context, and recent memory. Returns markdown formatted PR body.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp}},
        },
        "mnemo_dead_code": {
            "description": "Detect potentially unused classes, methods, and functions in the codebase. Reports symbols only referenced in their definition file.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp}},
        },
        "mnemo_add_security_pattern": {
            "description": "Add a custom security pattern to watch for in code scans.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "name": {"type": "string", "description": "Pattern name"}, "regex": {"type": "string", "description": "Regex to match unsafe code"}, "severity": {"type": "string", "description": "low, medium, or high"}, "description": {"type": "string"}}, "required": ["name", "regex"]},
        },
        "mnemo_check_security": {
            "description": "Scan codebase for security issues (hardcoded secrets, SQL injection, eval, shell injection). Optionally scope to a single file.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "file": {"type": "string", "description": "Optional file path to scope scan"}}},
        },
        "mnemo_breaking_changes": {
            "description": "Detect breaking changes by comparing current public API against saved baseline. Use action='baseline' to save current state.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "action": {"type": "string", "description": "'check' (default) to detect changes, 'baseline' to save current API as baseline"}}},
        },
        "mnemo_add_regression": {
            "description": "Record a regression risk for a file — links a past bug to a file path.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "file": {"type": "string", "description": "File path with regression risk"}, "bug": {"type": "string", "description": "What the bug was"}, "fix": {"type": "string", "description": "How it was fixed"}, "test": {"type": "string", "description": "Test that covers this"}}, "required": ["file", "bug", "fix"]},
        },
        "mnemo_check_regressions": {
            "description": "Check if a file has known regression risks. Without a file, lists all regressions.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "file": {"type": "string", "description": "File to check (omit to list all)"}}},
        },
        "mnemo_drift": {
            "description": "Detect architecture drift — compare current code patterns against stored architectural decisions.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp}},
        },
        "mnemo_hooks_install": {
            "description": "Install Mnemo pre-commit git hook for security and pattern validation.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp}},
        },
        "mnemo_check": {
            "description": "Run pre-commit validations (security scan) on staged files.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp}},
        },
        "mnemo_add_correction": {
            "description": "Store an AI suggestion that was corrected by the user, so the same mistake is not repeated.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "suggestion": {"type": "string", "description": "What the AI suggested"}, "correction": {"type": "string", "description": "What the user corrected it to"}, "context": {"type": "string"}, "file": {"type": "string"}}, "required": ["suggestion", "correction"]},
        },
        "mnemo_corrections": {
            "description": "Show stored corrections (AI mistakes the user fixed). Helps avoid repeating errors.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "query": {"type": "string", "description": "Optional filter"}, "limit": {"type": "integer", "description": "Max results (default 20)"}, "offset": {"type": "integer", "description": "Skip first N results (default 0)"}}},
        },
        "mnemo_velocity": {
            "description": "Show development velocity metrics — commits/day, lines changed, activity by author.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp}},
        },
        "mnemo_links": {
            "description": "Show all linked repos in the multi-repo workspace.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp}},
        },
        "mnemo_cross_search": {
            "description": "Search across this repo AND all linked repos. Use when looking for code, APIs, or patterns that may live in sibling services.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "query": {"type": "string", "description": "What to search for across all repos"}, "namespace": {"type": "string", "description": "Search namespace: code, api, or knowledge (default: code)"}}, "required": ["query"]},
        },
        "mnemo_cross_impact": {
            "description": "Cross-repo impact analysis — find what breaks across ALL linked repos if you change a service, file, or API.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "query": {"type": "string", "description": "Service, file, or API to analyze impact for"}}, "required": ["query"]},
        },
        "mnemo_graph": {
            "description": "Query the knowledge graph. Actions: stats, neighbors, traverse, path, find, hubs. Use to explore code relationships, dependencies, and impact.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "action": {"type": "string", "description": "stats, neighbors, traverse, path, find, or hubs"}, "node": {"type": "string", "description": "Node name or ID to query"}, "target": {"type": "string", "description": "Target node (for path action)"}, "edge_type": {"type": "string", "description": "Filter by edge type: contains, defines, implements, inherits, calls, depends_on, affects, references, owns"}, "depth": {"type": "integer", "description": "Traversal depth (default 2)"}, "direction": {"type": "string", "description": "incoming, outgoing, or both (default both)"}, "type": {"type": "string", "description": "Node type filter for find action"}, "name": {"type": "string", "description": "Name pattern for find action"}}, "required": ["action"]},
        },
        "mnemo_plan": {
            "description": "Plan mode — create, track, and update task plans. Actions: create (new plan), done (mark task complete), add (add task to plan), remove (remove task), status (show progress). Plans auto-sync to TASKS.md.",
            "inputSchema": {"type": "object", "properties": {"repo_path": _rp, "action": {"type": "string", "description": "create, done, add, remove, or status"}, "title": {"type": "string", "description": "Plan title (for create) or task title (for add)"}, "tasks": {"type": "array", "items": {"type": "string"}, "description": "List of task descriptions (for create)"}, "task_id": {"type": "string", "description": "Task ID like MNO-801 (for done/remove)"}, "summary": {"type": "string", "description": "Completion summary (for done)"}, "plan": {"type": "string", "description": "Plan title to add task to (for add)"}, "priority": {"type": "string", "description": "high, medium, or low (for create)"}}, "required": ["action"]},
        },
    }

    _handlers = {
        "mnemo_recall": _recall,
        "mnemo_lookup": _lookup,
        "mnemo_remember": _remember,
        "mnemo_forget": _forget,
        "mnemo_search_memory": _search_mem,
        "mnemo_decide": _decide,
        "mnemo_context": _context,
        "mnemo_map": _map,
        "mnemo_intelligence": _intelligence,
        "mnemo_similar": _similar,
        "mnemo_context_for_task": _context_for_task,
        "mnemo_knowledge": _knowledge,
        "mnemo_discover_apis": _discover_apis,
        "mnemo_search_api": _search_api,
        "mnemo_add_review": _add_review,
        "mnemo_reviews": _reviews,
        "mnemo_add_error": _add_error,
        "mnemo_search_errors": _search_errors,
        "mnemo_dependencies": _dependencies,
        "mnemo_impact": _impact,
        "mnemo_onboarding": _onboarding,
        "mnemo_task": _task,
        "mnemo_task_done": _task_done,
        "mnemo_tests": _tests,
        "mnemo_health": _health,
        "mnemo_team": _team,
        "mnemo_who_touched": _who_touched,
        "mnemo_add_incident": _add_incident,
        "mnemo_incidents": _incidents,
        "mnemo_commit_message": _commit_message,
        "mnemo_pr_description": _pr_description,
        "mnemo_dead_code": _dead_code,
        "mnemo_add_security_pattern": _add_security_pattern,
        "mnemo_check_security": _check_security,
        "mnemo_breaking_changes": _breaking_changes,
        "mnemo_add_regression": _add_regression,
        "mnemo_check_regressions": _check_regressions,
        "mnemo_drift": _drift,
        "mnemo_hooks_install": _hooks_install,
        "mnemo_check": _check,
        "mnemo_add_correction": _add_correction,
        "mnemo_corrections": _corrections,
        "mnemo_velocity": _velocity,
        "mnemo_links": _links,
        "mnemo_cross_search": _cross_search,
        "mnemo_cross_impact": _cross_impact,
        "mnemo_graph": _graph_query,
        "mnemo_plan": _plan,
    }

    for name, handler in _handlers.items():
        register(name, handler, _schemas[name])


_register_all()
