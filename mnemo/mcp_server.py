"""MCP Server – Exposes Mnemo tools to Amazon Q."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .init import init
from .memory import add_memory, add_decision, save_context, recall, lookup
from .repo_map import save_repo_map
from .intelligence import generate_intelligence, find_similar
from .knowledge import search_knowledge, list_knowledge, init_knowledge
from .api_discovery import discover_apis, search_api
from .code_review import add_review, format_reviews
from .errors import add_error, search_errors
from .dependency_graph import format_graph, impact_analysis
from .onboarding import generate_onboarding
from .sprint import set_current_task, complete_task, get_current_task, format_tasks
from .test_intel import get_tests_for_file, get_coverage_summary
from .health import calculate_health
from .team_graph import get_experts, who_last_touched
from .incidents import add_incident, search_incidents, format_incidents
from .config import MNEMO_DIR


def _find_repo_root(start: Path | None = None) -> Path | None:
    """Walk up from start to find a directory containing .mnemo/."""
    current = start or Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / MNEMO_DIR).exists():
            return parent
    return None


def handle_tool_call(tool_name: str, arguments: dict) -> dict:
    """Route MCP tool calls."""
    # Auto-detect repo root, fallback to explicit path
    repo_path = arguments.get("repo_path")
    if repo_path:
        repo_root = Path(repo_path).resolve()
    else:
        repo_root = _find_repo_root()

    if tool_name == "mnemo_init":
        target = Path(repo_path).resolve() if repo_path else Path.cwd()
        msg = init(target)
        return {"content": [{"type": "text", "text": msg}]}

    if not repo_root:
        return {"content": [{"type": "text", "text": "No .mnemo/ found. Run `mnemo init` in your repo first."}], "isError": True}

    if tool_name == "mnemo_recall":
        data = recall(repo_root)
        if not data:
            return {"content": [{"type": "text", "text": "Memory is empty. Run mnemo_init first."}]}
        return {"content": [{"type": "text", "text": data}]}

    elif tool_name == "mnemo_lookup":
        query = arguments.get("query", "")
        if not query:
            return {"content": [{"type": "text", "text": "Please provide a file or folder name to look up."}], "isError": True}
        result = lookup(repo_root, query)
        return {"content": [{"type": "text", "text": result}]}

    elif tool_name == "mnemo_remember":
        entry = add_memory(repo_root, arguments["content"], arguments.get("category", "general"))
        return {"content": [{"type": "text", "text": f"Stored memory #{entry['id']}: {entry['content']}"}]}

    elif tool_name == "mnemo_decide":
        entry = add_decision(repo_root, arguments["decision"], arguments.get("reasoning", ""))
        return {"content": [{"type": "text", "text": f"Decision #{entry['id']} recorded: {entry['decision']}"}]}

    elif tool_name == "mnemo_context":
        save_context(repo_root, arguments.get("context", {}))
        return {"content": [{"type": "text", "text": "Context updated."}]}

    elif tool_name == "mnemo_map":
        out = save_repo_map(repo_root)
        return {"content": [{"type": "text", "text": f"Repo map regenerated: {out}"}]}

    elif tool_name == "mnemo_intelligence":
        report = generate_intelligence(repo_root)
        return {"content": [{"type": "text", "text": report}]}

    elif tool_name == "mnemo_similar":
        query = arguments.get("query", "")
        if not query:
            return {"content": [{"type": "text", "text": "Provide a pattern name (e.g. 'Handler', 'Service')"}], "isError": True}
        results = find_similar(repo_root, query)
        if not results:
            return {"content": [{"type": "text", "text": f"No similar implementations for '{query}'"}]}
        lines = [f"# Similar to '{query}'\n"]
        for r in results:
            lines.append(f"- **{r['file']}** — `{r['class']}`")
        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    elif tool_name == "mnemo_knowledge":
        query = arguments.get("query", "")
        if query:
            result = search_knowledge(repo_root, query)
        else:
            result = list_knowledge(repo_root)
        return {"content": [{"type": "text", "text": result}]}

    elif tool_name == "mnemo_discover_apis":
        report = discover_apis(repo_root)
        return {"content": [{"type": "text", "text": report}]}

    elif tool_name == "mnemo_search_api":
        query = arguments.get("query", "")
        if not query:
            return {"content": [{"type": "text", "text": "Provide an endpoint or schema name to search."}], "isError": True}
        result = search_api(repo_root, query)
        return {"content": [{"type": "text", "text": result}]}

    # --- Code Review ---
    elif tool_name == "mnemo_add_review":
        entry = add_review(repo_root, arguments["summary"],
                          arguments.get("files", []),
                          arguments.get("feedback", ""),
                          arguments.get("outcome", "approved"))
        return {"content": [{"type": "text", "text": f"Review #{entry['id']} stored."}]}

    elif tool_name == "mnemo_reviews":
        return {"content": [{"type": "text", "text": format_reviews(repo_root)}]}

    # --- Error Memory ---
    elif tool_name == "mnemo_add_error":
        entry = add_error(repo_root, arguments["error"], arguments["cause"],
                         arguments["fix"], arguments.get("file", ""),
                         arguments.get("tags", []))
        return {"content": [{"type": "text", "text": f"Error #{entry['id']} stored."}]}

    elif tool_name == "mnemo_search_errors":
        return {"content": [{"type": "text", "text": search_errors(repo_root, arguments.get("query", ""))}]}

    # --- Dependency Graph ---
    elif tool_name == "mnemo_dependencies":
        return {"content": [{"type": "text", "text": format_graph(repo_root)}]}

    elif tool_name == "mnemo_impact":
        return {"content": [{"type": "text", "text": impact_analysis(repo_root, arguments.get("query", ""))}]}

    # --- Onboarding ---
    elif tool_name == "mnemo_onboarding":
        return {"content": [{"type": "text", "text": generate_onboarding(repo_root)}]}

    # --- Sprint/Task ---
    elif tool_name == "mnemo_task":
        task_id = arguments.get("task_id", "")
        if not task_id:
            return {"content": [{"type": "text", "text": get_current_task(repo_root)}]}
        entry = set_current_task(repo_root, task_id,
                               arguments.get("description", ""),
                               arguments.get("files", []),
                               arguments.get("notes", ""))
        return {"content": [{"type": "text", "text": f"Task {task_id} set as active."}]}

    elif tool_name == "mnemo_task_done":
        result = complete_task(repo_root, arguments.get("task_id", ""), arguments.get("summary", ""))
        return {"content": [{"type": "text", "text": result}]}

    # --- Test Intelligence ---
    elif tool_name == "mnemo_tests":
        query = arguments.get("query", "")
        if query:
            return {"content": [{"type": "text", "text": get_tests_for_file(repo_root, query)}]}
        return {"content": [{"type": "text", "text": get_coverage_summary(repo_root)}]}

    # --- Code Health ---
    elif tool_name == "mnemo_health":
        return {"content": [{"type": "text", "text": calculate_health(repo_root)}]}

    # --- Team Graph ---
    elif tool_name == "mnemo_team":
        query = arguments.get("query", "")
        return {"content": [{"type": "text", "text": get_experts(repo_root, query)}]}

    elif tool_name == "mnemo_who_touched":
        return {"content": [{"type": "text", "text": who_last_touched(repo_root, arguments.get("query", ""))}]}

    # --- Incidents ---
    elif tool_name == "mnemo_add_incident":
        entry = add_incident(repo_root, arguments["title"],
                            arguments["what_happened"], arguments["root_cause"],
                            arguments["fix"], arguments.get("prevention", ""),
                            arguments.get("severity", "medium"),
                            arguments.get("services", []))
        return {"content": [{"type": "text", "text": f"Incident #{entry['id']} recorded."}]}

    elif tool_name == "mnemo_incidents":
        query = arguments.get("query", "")
        if query:
            return {"content": [{"type": "text", "text": search_incidents(repo_root, query)}]}
        return {"content": [{"type": "text", "text": format_incidents(repo_root)}]}

    return {"content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}], "isError": True}


TOOLS = [
    {
        "name": "mnemo_init",
        "description": "Initialize Mnemo in a repository. Creates .mnemo/ folder, generates repo map, and bootstraps memory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the repository root"}
            },
            "required": ["repo_path"],
        },
    },
    {
        "name": "mnemo_recall",
        "description": "Recall all stored memory, decisions, context, and repo map. YOU MUST call this at the START of every new chat to load project context before answering any questions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the repository root (auto-detected if omitted)"}
            },
        },
    },
    {
        "name": "mnemo_lookup",
        "description": "Look up detailed code structure for a specific file or folder. Returns full method signatures, imports, and class details. Use this when you need to understand a specific part of the codebase in depth.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the repository root (auto-detected if omitted)"},
                "query": {"type": "string", "description": "File name, folder name, or path fragment to search for (e.g. 'AuthService', 'Controllers', 'UserController.cs')"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "mnemo_remember",
        "description": "Store important information in persistent memory. Use this to save context, user preferences, patterns, or anything that should be remembered across chat sessions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the repository root (auto-detected if omitted)"},
                "content": {"type": "string", "description": "The information to remember"},
                "category": {"type": "string", "description": "Category: general, architecture, preference, pattern, bug, todo"},
            },
            "required": ["content"],
        },
    },
    {
        "name": "mnemo_decide",
        "description": "Record an architectural or design decision with reasoning. Use this whenever a significant technical choice is made.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the repository root (auto-detected if omitted)"},
                "decision": {"type": "string", "description": "The decision that was made"},
                "reasoning": {"type": "string", "description": "Why this decision was made"},
            },
            "required": ["decision"],
        },
    },
    {
        "name": "mnemo_context",
        "description": "Save or update project context (tech stack, conventions, preferences). Merges with existing context.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the repository root (auto-detected if omitted)"},
                "context": {"type": "object", "description": "Key-value pairs of project context to store"},
            },
            "required": ["context"],
        },
    },
    {
        "name": "mnemo_map",
        "description": "Regenerate the repo map. Use this after significant code changes to keep the structural map up to date.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the repository root (auto-detected if omitted)"}
            },
        },
    },
    {
        "name": "mnemo_intelligence",
        "description": "Generate a code intelligence report: architecture graph (service-to-service calls), dependency map, detected patterns and conventions, code ownership.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the repository root (auto-detected if omitted)"}
            },
        },
    },
    {
        "name": "mnemo_similar",
        "description": "Find similar implementations in the codebase. Use this when implementing something new to find existing patterns to follow (e.g. 'Handler' finds all handler implementations).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the repository root (auto-detected if omitted)"},
                "query": {"type": "string", "description": "Pattern name to search for (e.g. 'Handler', 'Service', 'Controller')"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "mnemo_knowledge",
        "description": "Search the project knowledge base (runbooks, architecture docs, standards, gotchas). Without a query, lists all available knowledge files.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the repository root (auto-detected if omitted)"},
                "query": {"type": "string", "description": "Search term (optional — omit to list all knowledge files)"},
            },
        },
    },
    {
        "name": "mnemo_discover_apis",
        "description": "Discover all API endpoints in the project. Parses OpenAPI/Swagger specs and controller annotations to build a complete API catalog.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the repository root (auto-detected if omitted)"}
            },
        },
    },
    {
        "name": "mnemo_search_api",
        "description": "Search for a specific API endpoint, schema, or service in the API catalog.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the repository root (auto-detected if omitted)"},
                "query": {"type": "string", "description": "Endpoint path, method name, or schema to search for"},
            },
            "required": ["query"],
        },
    },
    {"name": "mnemo_add_review", "description": "Store a code review summary with feedback and outcome.", "inputSchema": {"type": "object", "properties": {"repo_path": {"type": "string"}, "summary": {"type": "string", "description": "What was reviewed"}, "files": {"type": "array", "items": {"type": "string"}, "description": "Files involved"}, "feedback": {"type": "string", "description": "Review feedback"}, "outcome": {"type": "string", "description": "approved, rejected, or changes_requested"}}, "required": ["summary"]}},
    {"name": "mnemo_reviews", "description": "Show code review history.", "inputSchema": {"type": "object", "properties": {"repo_path": {"type": "string"}}}},
    {"name": "mnemo_add_error", "description": "Store an error → cause → fix mapping for future reference.", "inputSchema": {"type": "object", "properties": {"repo_path": {"type": "string"}, "error": {"type": "string", "description": "The error message or symptom"}, "cause": {"type": "string", "description": "Root cause"}, "fix": {"type": "string", "description": "How it was fixed"}, "file": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}}, "required": ["error", "cause", "fix"]}},
    {"name": "mnemo_search_errors", "description": "Search known errors for a matching issue. Use when user hits an error to check if it's been seen before.", "inputSchema": {"type": "object", "properties": {"repo_path": {"type": "string"}, "query": {"type": "string", "description": "Error message or keyword"}}, "required": ["query"]}},
    {"name": "mnemo_dependencies", "description": "Show the full service dependency graph — which service depends on which.", "inputSchema": {"type": "object", "properties": {"repo_path": {"type": "string"}}}},
    {"name": "mnemo_impact", "description": "Impact analysis — what breaks if you change a specific service or file.", "inputSchema": {"type": "object", "properties": {"repo_path": {"type": "string"}, "query": {"type": "string", "description": "Service or file name to analyze"}}, "required": ["query"]}},
    {"name": "mnemo_onboarding", "description": "Generate a complete project onboarding guide for new team members.", "inputSchema": {"type": "object", "properties": {"repo_path": {"type": "string"}}}},
    {"name": "mnemo_task", "description": "Set or get the current task/ticket being worked on. Without task_id, shows active tasks.", "inputSchema": {"type": "object", "properties": {"repo_path": {"type": "string"}, "task_id": {"type": "string", "description": "Ticket ID (e.g. JIRA-123)"}, "description": {"type": "string"}, "files": {"type": "array", "items": {"type": "string"}}, "notes": {"type": "string"}}}},
    {"name": "mnemo_task_done", "description": "Mark a task as completed.", "inputSchema": {"type": "object", "properties": {"repo_path": {"type": "string"}, "task_id": {"type": "string"}, "summary": {"type": "string"}}, "required": ["task_id"]}},
    {"name": "mnemo_tests", "description": "Show which tests cover a file, or get overall test coverage summary. Use when modifying code to know what tests to run.", "inputSchema": {"type": "object", "properties": {"repo_path": {"type": "string"}, "query": {"type": "string", "description": "File name to find tests for (omit for coverage summary)"}}}},
    {"name": "mnemo_health", "description": "Code health report — complexity hotspots, large files, potential god classes.", "inputSchema": {"type": "object", "properties": {"repo_path": {"type": "string"}}}},
    {"name": "mnemo_team", "description": "Show team expertise map — who knows what based on git history.", "inputSchema": {"type": "object", "properties": {"repo_path": {"type": "string"}, "query": {"type": "string", "description": "Service or area to find experts for (omit for full map)"}}}},
    {"name": "mnemo_who_touched", "description": "Find who last modified a specific file.", "inputSchema": {"type": "object", "properties": {"repo_path": {"type": "string"}, "query": {"type": "string", "description": "File path or name"}}, "required": ["query"]}},
    {"name": "mnemo_add_incident", "description": "Record a production incident with root cause and fix.", "inputSchema": {"type": "object", "properties": {"repo_path": {"type": "string"}, "title": {"type": "string"}, "what_happened": {"type": "string"}, "root_cause": {"type": "string"}, "fix": {"type": "string"}, "prevention": {"type": "string"}, "severity": {"type": "string", "description": "low, medium, high, critical"}, "services": {"type": "array", "items": {"type": "string"}}}, "required": ["title", "what_happened", "root_cause", "fix"]}},
    {"name": "mnemo_incidents", "description": "Search or list production incidents.", "inputSchema": {"type": "object", "properties": {"repo_path": {"type": "string"}, "query": {"type": "string", "description": "Search term (omit to list all)"}}}},
]


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
                    "serverInfo": {"name": "mnemo", "version": "0.1.0"},
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
