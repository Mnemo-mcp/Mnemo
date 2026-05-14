"""Fact extraction from agent responses (MNO-014)."""

from __future__ import annotations

import re

# Pattern → category mapping
_PATTERNS = [
    (re.compile(r"(?:decided|chose|decision:)\s+(.{10,150})", re.I), "decision"),
    (re.compile(r"(?:fixed|issue was|bug was|the problem was)\s+(.{10,150})", re.I), "bug"),
    (re.compile(r"(?:prefer|convention:|user prefers)\s+(.{10,150})", re.I), "preference"),
    (re.compile(r"(?:pattern:|always)\s+(.{10,150})", re.I), "pattern"),
]

MIN_RESPONSE_LENGTH = 100
MAX_EXTRACTIONS = 2


def extract_facts(response: str) -> list[dict[str, str]]:
    """Extract facts from an agent response. Returns list of {content, category}."""
    if not response or len(response) < MIN_RESPONSE_LENGTH:
        return []
    facts: list[dict[str, str]] = []
    for pattern, category in _PATTERNS:
        if len(facts) >= MAX_EXTRACTIONS:
            break
        match = pattern.search(response)
        if match:
            content = match.group(1).strip().rstrip(".")
            facts.append({"content": content, "category": category})
    return facts
