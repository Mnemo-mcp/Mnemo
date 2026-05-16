"""Memory & Context tools."""

from __future__ import annotations

from pathlib import Path

from ..tool_registry import tool


@tool("mnemo_recall",
      "Recall all stored memory, decisions, context, and repo map. YOU MUST call this at the START of every new chat to load project context before answering any questions.",
      properties={
          "tier": {"type": "string", "description": "Recall tier: compact (~500 tokens), standard (~2000 tokens), or deep (unlimited). Default: standard"},
      })
def _recall(root: Path, args: dict) -> str:
    from ..memory import recall
    tier = args.get("tier", "standard")
    data = recall(root, tier=tier)
    return data or "Memory is empty. Run mnemo_init first."


@tool("mnemo_remember",
      "Store important information in persistent memory. Use this to save context, user preferences, patterns, or anything that should be remembered across chat sessions.",
      properties={
          "content": {"type": "string", "description": "The information to remember"},
          "category": {"type": "string", "description": "Category: general, architecture, preference, pattern, bug, todo"},
      },
      required=["content"])
def _remember(root: Path, args: dict) -> str:
    from ..memory.services import remember_with_effects
    return remember_with_effects(root, args["content"], args.get("category", "general"))


@tool("mnemo_forget",
      "Delete a specific memory entry by ID. Use when a memory is wrong or outdated.",
      properties={"memory_id": {"type": "integer", "description": "ID of the memory to delete"}},
      required=["memory_id"])
def _forget(root: Path, args: dict) -> str:
    from ..memory import forget_memory
    return forget_memory(root, int(args.get("memory_id", 0)))


@tool("mnemo_search_memory",
      "Search stored memories semantically. Use when mnemo_recall does not have enough context. Auto-detects relevant category from your query.",
      properties={
          "query": {"type": "string", "description": "What to search for in memory (e.g. auth token bug, caching decision)"},
          "deep": {"type": "boolean", "description": "Set true for more results (15 instead of 7)"},
      },
      required=["query"])
def _search_mem(root: Path, args: dict) -> str:
    from ..memory import search_memory
    return search_memory(root, args.get("query", ""), deep=args.get("deep", False))


@tool("mnemo_decide",
      "Record an architectural or design decision with reasoning. Use this whenever a significant technical choice is made.",
      properties={
          "decision": {"type": "string", "description": "The decision that was made"},
          "reasoning": {"type": "string", "description": "Why this decision was made"},
      },
      required=["decision"])
def _decide(root: Path, args: dict) -> str:
    from ..memory.services import decide_with_effects
    return decide_with_effects(root, args["decision"], args.get("reasoning", ""))


@tool("mnemo_context",
      "Save or update project context (tech stack, conventions, preferences). Merges with existing context.",
      properties={"context": {"type": "object", "description": "Key-value pairs of project context to store"}},
      required=["context"])
def _context(root: Path, args: dict) -> str:
    from ..memory import save_context
    ctx = args.get("context", {})
    if isinstance(ctx, str):
        # Parse "key=value" or "key: value" pairs from string
        pairs = {}
        for part in ctx.replace(";", "\n").split("\n"):
            for sep in ("=", ":"):
                if sep in part:
                    k, v = part.split(sep, 1)
                    pairs[k.strip()] = v.strip()
                    break
        ctx = pairs if pairs else {"note": ctx}
    save_context(root, ctx)
    return "Context updated."


@tool("mnemo_slot_get",
      "Get the content of a named memory slot.",
      properties={"name": {"type": "string", "description": "Slot name (project_context, user_preferences, conventions, pending_items, known_gotchas)"}},
      required=["name"])
def _slot_get(root: Path, args: dict) -> str:
    from ..memory.slots import get_slot
    return get_slot(root, args.get("name", ""))


@tool("mnemo_slot_set",
      "Set the content of a named memory slot.",
      properties={
          "name": {"type": "string", "description": "Slot name"},
          "content": {"type": "string", "description": "Content to store in the slot"},
      },
      required=["name", "content"])
def _slot_set(root: Path, args: dict) -> str:
    from ..memory.slots import set_slot
    return set_slot(root, args.get("name", ""), args.get("content", ""))


@tool("mnemo_lesson",
      "Lessons system — store, list, or decay learned patterns. Actions: add, list, decay.",
      properties={
          "action": {"type": "string", "description": "add, list, or decay"},
          "content": {"type": "string", "description": "Lesson content (for add)"},
          "source": {"type": "string", "description": "Source of the lesson (for add)"},
          "min_confidence": {"type": "number", "description": "Minimum confidence filter (for list, default 0.3)"},
      },
      required=["action"])
def _lesson(root: Path, args: dict) -> str:
    from ..memory.lessons import add_lesson, get_lessons, decay_lessons
    action = args.get("action", "list")
    if action == "add":
        content = args.get("content", "")
        if not content:
            return "Content is required."
        entry = add_lesson(root, content, source=args.get("source", ""))
        if entry.get("reinforcement_count", 0) > 0:
            return f"Lesson #{entry['id']} reinforced (confidence: {entry['confidence']:.2f})"
        return f"Lesson #{entry['id']} added (confidence: {entry['confidence']:.2f})"
    elif action == "decay":
        return decay_lessons(root)
    else:
        lessons = get_lessons(root, min_confidence=float(args.get("min_confidence", 0.3)))
        if not lessons:
            return "No active lessons."
        lines = ["# Lessons\n"]
        for entry in lessons:
            lines.append(f"- [{entry['confidence']:.2f}] {entry['content']}")
        return "\n".join(lines)
