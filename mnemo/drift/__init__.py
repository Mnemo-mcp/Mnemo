"""Architecture drift detection - compare current patterns against stored decisions."""

from __future__ import annotations

import re
from pathlib import Path

from ..storage import Collections, get_storage
from ..intelligence import generate_intelligence


# Patterns to extract structured intent from decision text
_USE_PATTERNS = re.compile(
    r"\b(?:use|chose|using|adopt|switch(?:ed)? to|migrat(?:e|ed) to)\s+([A-Za-z0-9_.\-/]+)", re.I
)
_AVOID_PATTERNS = re.compile(
    r"\b(?:never|avoid|don'?t use|do not use|deprecat(?:e|ed)|remov(?:e|ed)|ban)\s+([A-Za-z0-9_.\-/]+)", re.I
)
_REQUIRE_PATTERNS = re.compile(
    r"\b(?:must|always|require|enforce|all .+ must)\s+(.+?)(?:\.|$)", re.I
)


def _extract_intents(text: str) -> dict:
    """Extract structured intents from a decision's text."""
    intents = {"use": [], "avoid": [], "require": []}

    for match in _USE_PATTERNS.finditer(text):
        term = match.group(1).strip(".,;")
        if len(term) > 2:
            intents["use"].append(term.lower())

    for match in _AVOID_PATTERNS.finditer(text):
        term = match.group(1).strip(".,;")
        if len(term) > 2:
            intents["avoid"].append(term.lower())

    for match in _REQUIRE_PATTERNS.finditer(text):
        term = match.group(1).strip(".,;")
        if len(term) > 3:
            intents["require"].append(term.lower())

    return intents


def detect_drift(repo_root: Path) -> str:
    """Compare current code patterns against stored architectural decisions."""
    storage = get_storage(repo_root)
    decisions = storage.read_collection(Collections.DECISIONS)
    if not isinstance(decisions, list) or not decisions:
        return "No architectural decisions stored. Use `mnemo_decide` to record decisions first."

    # Get current intelligence report
    report = generate_intelligence(repo_root)
    report_lower = report.lower()

    drifts = []

    for decision in decisions:
        text = decision.get("decision", "") + " " + decision.get("reasoning", "")
        intents = _extract_intents(text)
        issues = []

        # Check "use X" — X should appear in current architecture
        for term in intents["use"]:
            if term not in report_lower:
                issues.append(f"Decision says use `{term}` but not found in current architecture")

        # Check "avoid X" — X should NOT appear in current architecture
        for term in intents["avoid"]:
            if term in report_lower:
                issues.append(f"Decision says avoid `{term}` but it appears in current code")

        if issues:
            drifts.append({"decision": decision.get("decision", ""), "issues": issues})

    if not drifts:
        return "No architecture drift detected. Current code aligns with stored decisions."

    lines = [f"# Architecture Drift ({len(drifts)} potential issues)\n"]
    for d in drifts:
        lines.append(f"## Decision: {d['decision'][:100]}")
        for issue in d["issues"]:
            lines.append(f"- \u26a0\ufe0f {issue}")
        lines.append("")

    lines.append("*Review these to confirm if drift is intentional or needs correction.*")
    return "\n".join(lines)
