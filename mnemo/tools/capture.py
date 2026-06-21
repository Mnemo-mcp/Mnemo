"""Auto-capture tool — classifies user messages and persists decisions/preferences automatically.

Called by the user-prompt-submit hook on every user message.
Uses embedding-based intent classification (not regex) to decide what to persist.
"""

from __future__ import annotations

from pathlib import Path

from ..tool_registry import tool


@tool("mnemo_auto_capture",
      "Classify a user message and auto-persist decisions/preferences. Called by hooks, not by agents directly.",
      properties={
          "message": {"type": "string", "description": "The user message to classify"},
      },
      required=["message"])
def _auto_capture(root: Path, args: dict) -> str:
    message = args.get("message", "").strip()
    if not message or len(message) < 10:
        return "skip: too short"

    # Skip questions and instructions
    lower = message.lower().strip()
    if lower.startswith(('what ', 'how ', 'why ', 'where ', 'when ', 'who ', 'which ', 'is ', 'are ', 'can ', 'could ', 'would ', 'should ', 'does ', 'do ', 'will ')):
        return 'skip: question'
    if lower.startswith(('run ', 'check ', 'show ', 'tell ', 'find ', 'look ', 'search ', 'list ', 'create ', 'add ', 'delete ', 'remove ', 'fix ', 'implement ', 'refactor ', 'debug ', 'test ', 'deploy ', 'build ', 'install ', 'update ', 'upgrade ', 'generate ', 'also ', 'include ')):
        return 'skip: instruction'

    from ..intent import classify_intent, extract_decisions
    from ..memory.services import remember_with_effects

    # Classify the full message first
    result = classify_intent(message)

    if not result["is_decision"]:
        return "skip: not a decision"

    # For multi-sentence messages, extract specific decision sentences
    decisions = extract_decisions(message, threshold=0.25)

    if not decisions:
        return "skip: no extractable decisions"

    # Persist each decision
    saved = []
    for decision in decisions[:3]:  # Cap at 3 per message
        # Infer category from content
        category = _infer_category(decision)
        remember_with_effects(root, decision, category)
        saved.append(f"{category}: {decision[:80]}")

    return f"captured {len(saved)}: " + "; ".join(saved)


def _infer_category(text: str) -> str:
    """Infer the best memory category for a decision."""
    lower = text.lower()

    # Architecture: tech choices, deployment, infrastructure
    if any(w in lower for w in ("database", "deploy", "architecture", "microservice",
                                 "monorepo", "api", "backend", "frontend", "stack",
                                 "framework", "infrastructure")):
        return "architecture"

    # Preference: style, conventions, tools, communication
    if any(w in lower for w in ("prefer", "convention", "style", "font", "theme",
                                 "color", "design", "team uses", "we use",
                                 "not", "instead", "actually", "wrong")):
        return "preference"

    # Pattern: code patterns, standards
    if any(w in lower for w in ("pattern", "standard", "follow", "naming")):
        return "pattern"

    return "preference"  # Default for decisions
