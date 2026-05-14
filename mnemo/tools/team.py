"""Team & Operations tools."""

from __future__ import annotations

from pathlib import Path

from ..tool_registry import tool


@tool("mnemo_add_review",
      "Store a code review summary with feedback and outcome.",
      properties={
          "summary": {"type": "string", "description": "What was reviewed"},
          "files": {"type": "array", "items": {"type": "string"}, "description": "Files involved"},
          "feedback": {"type": "string", "description": "Review feedback"},
          "outcome": {"type": "string", "description": "approved, rejected, or changes_requested"},
      },
      required=["summary"])
def _add_review(root: Path, args: dict) -> str:
    from ..code_review import add_review
    entry = add_review(root, args["summary"], args.get("files", []),
                       args.get("feedback", ""), args.get("outcome", "approved"))
    return f"Review #{entry['id']} stored."


@tool("mnemo_reviews",
      "Show code review history.",
      properties={
          "limit": {"type": "integer", "description": "Max results (default 20)"},
          "offset": {"type": "integer", "description": "Skip first N results (default 0)"},
      })
def _reviews(root: Path, args: dict) -> str:
    from ..code_review import format_reviews
    return format_reviews(root, limit=int(args.get("limit", 20)), offset=int(args.get("offset", 0)))


@tool("mnemo_add_error",
      "Store an error → cause → fix mapping for future reference.",
      properties={
          "error": {"type": "string", "description": "The error message or symptom"},
          "cause": {"type": "string", "description": "Root cause"},
          "fix": {"type": "string", "description": "How it was fixed"},
          "file": {"type": "string"},
          "tags": {"type": "array", "items": {"type": "string"}},
      },
      required=["error", "cause", "fix"])
def _add_error(root: Path, args: dict) -> str:
    from ..errors import add_error
    entry = add_error(root, args["error"], args["cause"], args["fix"],
                      args.get("file", ""), args.get("tags", []))
    return f"Error #{entry['id']} stored."


@tool("mnemo_search_errors",
      "Search known errors for a matching issue. Use when user hits an error to check if it's been seen before.",
      properties={"query": {"type": "string", "description": "Error message or keyword"}},
      required=["query"])
def _search_errors(root: Path, args: dict) -> str:
    from ..errors import search_errors
    return search_errors(root, args.get("query", ""))


@tool("mnemo_dependencies",
      "Show the full service dependency graph — which service depends on which.")
def _dependencies(root: Path, args: dict) -> str:
    from ..dependency_graph import format_graph
    return format_graph(root)


@tool("mnemo_impact",
      "Impact analysis — what breaks if you change a specific service or file.",
      properties={"query": {"type": "string", "description": "Service or file name to analyze"}},
      required=["query"])
def _impact(root: Path, args: dict) -> str:
    from ..dependency_graph import impact_analysis
    return impact_analysis(root, args.get("query", ""))


@tool("mnemo_onboarding",
      "Generate a complete project onboarding guide for new team members.")
def _onboarding(root: Path, args: dict) -> str:
    from ..onboarding import generate_onboarding
    return generate_onboarding(root)


@tool("mnemo_task",
      "Set or get the current task/ticket being worked on. Without task_id, shows active tasks.",
      properties={
          "task_id": {"type": "string", "description": "Ticket ID (e.g. JIRA-123)"},
          "description": {"type": "string"},
          "files": {"type": "array", "items": {"type": "string"}},
          "notes": {"type": "string"},
      })
def _task(root: Path, args: dict) -> str:
    from ..sprint import set_current_task, get_current_task
    task_id = args.get("task_id", "")
    if not task_id:
        return get_current_task(root)
    set_current_task(root, task_id, args.get("description", ""),
                     args.get("files", []), args.get("notes", ""))
    return f"Task {task_id} set as active."


@tool("mnemo_task_done",
      "Mark a task as completed.",
      properties={
          "task_id": {"type": "string"},
          "summary": {"type": "string"},
      },
      required=["task_id"])
def _task_done(root: Path, args: dict) -> str:
    from ..sprint import complete_task, _load_tasks
    from ..storage import Collections, get_storage
    from ..memory import add_memory

    result = complete_task(root, args.get("task_id", ""), args.get("summary", ""))
    task_id = args.get("task_id", "")
    summary = args.get("summary", "")
    try:
        tasks = _load_tasks(root)
        task_entry = next((t for t in tasks if t.get("task_id") == task_id), None)
        if task_entry:
            desc = task_entry.get("description", task_id)
            files = task_entry.get("files", [])
            storage = get_storage(root)
            memories = storage.read_collection(Collections.MEMORY)
            if not isinstance(memories, list):
                memories = []
            decisions = [m for m in memories[-10:] if m.get("category") == "decision"]
            decision_text = "; ".join(d.get("content", "")[:50] for d in decisions[:3])
            crystal = f"Completed [{desc}]: {summary or 'done'}. Files: {', '.join(files[:5]) or 'none'}."
            if decision_text:
                crystal += f" Decisions: {decision_text}"
            add_memory(root, crystal, "pattern", source="crystal")
            errors = [m for m in memories[-10:] if m.get("category") == "bug"]
            for err in errors[:2]:
                lesson = f"Lesson from {task_id}: {err.get('content', '')[:100]}"
                add_memory(root, lesson, "pattern", source="lesson")
    except Exception as exc:
        from ..utils.logger import get_logger
        get_logger("tools.team").debug(f"Crystallization failed: {exc}")
    return result


@tool("mnemo_tests",
      "Show which tests cover a file, or get overall test coverage summary. Use when modifying code to know what tests to run.",
      properties={"query": {"type": "string", "description": "File name to find tests for (omit for coverage summary)"}})
def _tests(root: Path, args: dict) -> str:
    from ..test_intel import get_tests_for_file, get_coverage_summary
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


@tool("mnemo_add_incident",
      "Record a production incident with root cause and fix.",
      properties={
          "title": {"type": "string"},
          "what_happened": {"type": "string"},
          "root_cause": {"type": "string"},
          "fix": {"type": "string"},
          "prevention": {"type": "string"},
          "severity": {"type": "string", "description": "low, medium, high, critical"},
          "services": {"type": "array", "items": {"type": "string"}},
      },
      required=["title", "what_happened", "root_cause", "fix"])
def _add_incident(root: Path, args: dict) -> str:
    from ..incidents import add_incident
    entry = add_incident(root, args["title"], args["what_happened"],
                         args["root_cause"], args["fix"],
                         args.get("prevention", ""), args.get("severity", "medium"),
                         args.get("services", []))
    return f"Incident #{entry['id']} recorded."


@tool("mnemo_incidents",
      "Search or list production incidents.",
      properties={
          "query": {"type": "string", "description": "Search term (omit to list all)"},
          "limit": {"type": "integer", "description": "Max results (default 20)"},
          "offset": {"type": "integer", "description": "Skip first N results (default 0)"},
      })
def _incidents(root: Path, args: dict) -> str:
    from ..incidents import search_incidents, format_incidents
    query = args.get("query", "")
    if query:
        return search_incidents(root, query)
    return format_incidents(root, limit=int(args.get("limit", 20)), offset=int(args.get("offset", 0)))


@tool("mnemo_add_correction",
      "Store an AI suggestion that was corrected by the user, so the same mistake is not repeated.",
      properties={
          "suggestion": {"type": "string", "description": "What the AI suggested"},
          "correction": {"type": "string", "description": "What the user corrected it to"},
          "context": {"type": "string"},
          "file": {"type": "string"},
      },
      required=["suggestion", "correction"])
def _add_correction(root: Path, args: dict) -> str:
    from ..corrections import add_correction
    entry = add_correction(root, args["suggestion"], args["correction"],
                           args.get("context", ""), args.get("file", ""))
    return f"Correction #{entry['id']} stored."


@tool("mnemo_corrections",
      "Show stored corrections (AI mistakes the user fixed). Helps avoid repeating errors.",
      properties={
          "query": {"type": "string", "description": "Optional filter"},
          "limit": {"type": "integer", "description": "Max results (default 20)"},
          "offset": {"type": "integer", "description": "Skip first N results (default 0)"},
      })
def _corrections(root: Path, args: dict) -> str:
    from ..corrections import get_corrections
    return get_corrections(root, args.get("query", ""),
                           limit=int(args.get("limit", 20)), offset=int(args.get("offset", 0)))
