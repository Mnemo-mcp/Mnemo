"""Architecture drift detection - graph-based + rules.yaml validation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from ..config import mnemo_path
from ..storage import Collections, get_storage
from ..intelligence import generate_intelligence


RULES_FILE = "rules.yaml"

# Patterns to extract structured intent from decision text
_USE_PATTERNS = re.compile(
    r"\b(?:use|chose|using|adopt|switch(?:ed)? to|migrat(?:e|ed) to)\s+([A-Za-z0-9_.\-/]+)", re.I
)
_AVOID_PATTERNS = re.compile(
    r"\b(?:never|avoid|don'?t use|do not use|deprecat(?:e|ed)|remov(?:e|ed)|ban)\s+([A-Za-z0-9_.\-/]+)", re.I
)


def _extract_intents(text: str) -> dict:
    """Extract structured intents from a decision's text."""
    intents = {"use": [], "avoid": []}
    for match in _USE_PATTERNS.finditer(text):
        term = match.group(1).strip(".,;")
        if len(term) > 2:
            intents["use"].append(term.lower())
    for match in _AVOID_PATTERNS.finditer(text):
        term = match.group(1).strip(".,;")
        if len(term) > 2:
            intents["avoid"].append(term.lower())
    return intents


def _load_rules(repo_root: Path) -> list[dict[str, Any]]:
    """Load architectural rules from .mnemo/rules.yaml."""
    path = mnemo_path(repo_root) / RULES_FILE
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data.get("rules", []) if isinstance(data, dict) else []
    except Exception:
        return []


def _check_graph_rules(repo_root: Path) -> list[dict[str, Any]]:
    """Check layer violation rules against the knowledge graph."""
    rules = _load_rules(repo_root)
    if not rules:
        return []

    try:
        from ..graph.local import LocalGraph
        graph = LocalGraph(repo_root)
        if not graph.exists():
            return []
    except Exception:
        return []

    violations = []
    for rule in rules:
        source_layer = rule.get("source", "").lower()
        forbidden_target = rule.get("cannot_access", "").lower()
        description = rule.get("description", f"{source_layer} cannot access {forbidden_target}")

        if not source_layer or not forbidden_target:
            continue

        # Find nodes matching source layer
        for nid, data in graph.graph.nodes(data=True):
            node_name = data.get("name", "").lower()
            data.get("type", "")

            if source_layer not in node_name:
                continue

            # Check outgoing edges for forbidden targets
            for _, target_id, edge_data in graph.graph.out_edges(nid, data=True):
                target_data = graph.graph.nodes.get(target_id, {})
                target_name = target_data.get("name", "").lower()
                if forbidden_target in target_name:
                    violations.append({
                        "rule": description,
                        "source": data.get("name", nid),
                        "target": target_data.get("name", target_id),
                        "edge_type": edge_data.get("type", "unknown"),
                    })

    return violations


def _check_decision_drift(repo_root: Path) -> list[dict[str, Any]]:
    """Check decisions against current architecture (text-based)."""
    storage = get_storage(repo_root)
    decisions = storage.read_collection(Collections.DECISIONS)
    if not isinstance(decisions, list) or not decisions:
        return []

    report = generate_intelligence(repo_root)
    report_lower = report.lower()
    drifts = []

    for decision in decisions:
        text = decision.get("decision", "") + " " + decision.get("reasoning", "")
        intents = _extract_intents(text)
        issues = []

        for term in intents["use"]:
            if term not in report_lower:
                issues.append(f"Decision says use `{term}` but not found in current architecture")
        for term in intents["avoid"]:
            if term in report_lower:
                issues.append(f"Decision says avoid `{term}` but it appears in current code")

        if issues:
            drifts.append({"decision": decision.get("decision", ""), "issues": issues})

    return drifts


def detect_drift(repo_root: Path) -> str:
    """Compare current code against architectural rules and stored decisions."""
    # Check graph-based rules first
    graph_violations = _check_graph_rules(repo_root)

    # Check decision-based drift
    decision_drifts = _check_decision_drift(repo_root)

    if not graph_violations and not decision_drifts:
        return "No architecture drift detected. Current code aligns with stored decisions and rules."

    lines = []

    if graph_violations:
        lines.append(f"# Layer Violations ({len(graph_violations)} found)\n")
        for v in graph_violations:
            lines.append(f"- ⛔ **{v['rule']}**")
            lines.append(f"  `{v['source']}` --{v['edge_type']}--> `{v['target']}`")
        lines.append("")

    if decision_drifts:
        lines.append(f"# Decision Drift ({len(decision_drifts)} potential issues)\n")
        for d in decision_drifts:
            lines.append(f"## Decision: {d['decision'][:100]}")
            for issue in d["issues"]:
                lines.append(f"- ⚠️ {issue}")
            lines.append("")

    lines.append("*Review these to confirm if drift is intentional or needs correction.*")
    return "\n".join(lines)


def _init_rules(repo_root: Path) -> None:
    """Create default rules.yaml if it doesn't exist."""
    path = mnemo_path(repo_root) / RULES_FILE
    if path.exists():
        return
    default = {
        "rules": [
            {
                "source": "controller",
                "cannot_access": "repository",
                "description": "Controllers cannot access repositories directly (must go through services)",
            },
            {
                "source": "controller",
                "cannot_access": "database",
                "description": "Controllers cannot access databases directly",
            },
        ]
    }
    try:
        path.write_text(yaml.dump(default, default_flow_style=False), encoding="utf-8")
    except (OSError, PermissionError):
        pass  # Non-critical: rules file write failure
