"""Meta-tool mnemo_ask — intent-based routing that calls multiple tools (MNO-847)."""

from __future__ import annotations

import re
from pathlib import Path


# Intent patterns
_INTENTS = {
    "architecture": re.compile(r"\b(architecture|structure|design|layers|services)\b", re.I),
    "impact": re.compile(r"\b(impact|break|change|affect|depend)\b", re.I),
    "why": re.compile(r"\b(why|reason|purpose|exist|introduced)\b", re.I),
    "ownership": re.compile(r"\b(who|owner|team|expert|touch)\b", re.I),
    "health": re.compile(r"\b(health|quality|complexity|debt|hotspot)\b", re.I),
    "security": re.compile(r"\b(security|secret|vulnerab|inject|leak)\b", re.I),
    "history": re.compile(r"\b(history|incident|error|bug|regression|past)\b", re.I),
    "plan": re.compile(r"\b(plan|task|progress|status|next|todo)\b", re.I),
}


def classify_intent(query: str) -> str:
    """Classify user intent from natural language query."""
    scores: dict[str, int] = {}
    for intent, pattern in _INTENTS.items():
        matches = pattern.findall(query)
        if matches:
            scores[intent] = len(matches)
    if not scores:
        return "general"
    return max(scores, key=scores.get)


def ask(repo_root: Path, query: str) -> str:
    """Route a natural language query to the appropriate tools and combine results."""
    intent = classify_intent(query)

    # Extract entity from query (longest capitalized word or quoted string)
    entity = _extract_entity(query)

    from .tool_registry import get_handler

    results = []

    if intent == "architecture":
        handler = get_handler("mnemo_intelligence")
        if handler:
            results.append(handler(repo_root, {}))

    elif intent == "impact":
        handler = get_handler("mnemo_impact")
        if handler and entity:
            results.append(handler(repo_root, {"query": entity}))

    elif intent == "why":
        handler = get_handler("mnemo_graph")
        if handler and entity:
            results.append(handler(repo_root, {"action": "why", "node": entity}))

    elif intent == "ownership":
        handler = get_handler("mnemo_who_touched")
        if handler and entity:
            results.append(handler(repo_root, {"query": entity}))
        handler = get_handler("mnemo_team")
        if handler:
            results.append(handler(repo_root, {"query": entity or ""}))

    elif intent == "health":
        handler = get_handler("mnemo_health")
        if handler:
            results.append(handler(repo_root, {}))

    elif intent == "security":
        handler = get_handler("mnemo_check_security")
        if handler:
            results.append(handler(repo_root, {"file": entity or ""}))

    elif intent == "history":
        handler = get_handler("mnemo_search_errors")
        if handler and entity:
            results.append(handler(repo_root, {"query": entity}))
        handler = get_handler("mnemo_incidents")
        if handler:
            results.append(handler(repo_root, {"query": entity or ""}))

    elif intent == "plan":
        handler = get_handler("mnemo_plan")
        if handler:
            results.append(handler(repo_root, {"action": "status"}))

    else:
        # General: try lookup + search memory
        handler = get_handler("mnemo_lookup")
        if handler and entity:
            results.append(handler(repo_root, {"query": entity}))
        handler = get_handler("mnemo_search_memory")
        if handler:
            results.append(handler(repo_root, {"query": query}))

    if not results:
        return f"No results for: {query}"

    return "\n\n---\n\n".join(r for r in results if r)


def _extract_entity(query: str) -> str:
    """Extract the main entity/subject from a query."""
    # Try quoted strings first
    quoted = re.findall(r'["\']([^"\']+)["\']', query)
    if quoted:
        return quoted[0]
    # Try PascalCase/camelCase words
    pascal = re.findall(r'\b([A-Z][a-zA-Z]+(?:Service|Handler|Controller|Repository|Manager|Factory))\b', query)
    if pascal:
        return pascal[0]
    # Try any capitalized word > 3 chars
    caps = re.findall(r'\b([A-Z][a-zA-Z]{3,})\b', query)
    if caps:
        return caps[0]
    # Last resort: longest word
    words = [w for w in query.split() if len(w) > 3 and w not in ("what", "does", "this", "that", "from", "with")]
    return max(words, key=len) if words else ""
