"""Architecture drift detection — uses engine/ graph for layer violation checks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..config import mnemo_path
from ..storage import Collections, get_storage

RULES_FILE = "rules.yaml"

_USE_PATTERNS = re.compile(r"\b(?:use|chose|using|adopt|switch(?:ed)? to|migrat(?:e|ed) to)\s+([A-Za-z0-9_.\-/]+)", re.I)
_AVOID_PATTERNS = re.compile(r"\b(?:never|avoid|don'?t use|do not use|deprecat(?:e|ed)|remov(?:e|ed)|ban)\s+([A-Za-z0-9_.\-/]+)", re.I)


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
    import yaml
    path = mnemo_path(repo_root) / RULES_FILE
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data.get("rules", []) if isinstance(data, dict) else []
    except Exception:
        return []


def _check_graph_rules(repo_root: Path) -> list[dict[str, Any]]:
    """Check layer violation rules against LadybugDB graph."""
    rules = _load_rules(repo_root)
    if not rules:
        return []

    try:
        from ..engine.db import open_db, get_db_path
        if not get_db_path(repo_root).exists():
            return []
        _, conn = open_db(repo_root)
    except Exception:
        return []

    violations = []
    for rule in rules:
        source_layer = rule.get("source", "").lower()
        forbidden_target = rule.get("cannot_access", "").lower()
        description = rule.get("description", f"{source_layer} cannot access {forbidden_target}")
        if not source_layer or not forbidden_target:
            continue

        # Check IMPORTS edges: files in source_layer importing files in forbidden_target
        try:
            result = conn.execute(f"""
                MATCH (a:File)-[:IMPORTS]->(b:File)
                WHERE toLower(a.path) CONTAINS '{source_layer}'
                AND toLower(b.path) CONTAINS '{forbidden_target}'
                RETURN a.path, b.path
            """)
            while result.has_next():
                row = result.get_next()
                violations.append({"rule": description, "source": row[0], "target": row[1], "edge_type": "IMPORTS"})
        except RuntimeError:
            pass

    return violations


def _check_decision_drift(repo_root: Path) -> list[dict[str, Any]]:
    """Check decisions against current file/symbol names in graph."""
    storage = get_storage(repo_root)
    decisions = storage.read_collection(Collections.DECISIONS)
    if not isinstance(decisions, list) or not decisions:
        return []

    # Build a corpus from graph: all file paths + class/function names
    corpus = ""
    try:
        from ..engine.db import open_db, get_db_path
        if get_db_path(repo_root).exists():
            _, conn = open_db(repo_root)
            result = conn.execute("MATCH (f:File) RETURN f.path")
            paths = []
            while result.has_next():
                paths.append(result.get_next()[0])
            result = conn.execute("MATCH (c:Class) RETURN c.name")
            while result.has_next():
                paths.append(result.get_next()[0])
            result = conn.execute("MATCH (f:Function) RETURN f.name")
            while result.has_next():
                paths.append(result.get_next()[0])
            corpus = " ".join(paths).lower()
    except Exception:
        pass

    if not corpus:
        return []

    drifts = []
    for decision in decisions:
        if not decision.get("active", True):
            continue
        text = decision.get("decision", "") + " " + decision.get("reasoning", "")
        intents = _extract_intents(text)
        issues = []
        for term in intents["use"]:
            if term not in corpus:
                issues.append(f"Decision says use `{term}` but not found in current codebase")
        for term in intents["avoid"]:
            if term in corpus:
                issues.append(f"Decision says avoid `{term}` but it appears in current code")
        if issues:
            drifts.append({"decision": decision.get("decision", "")[:100], "issues": issues})

    return drifts


def detect_drift(repo_root: Path) -> str:
    """Compare current code against architectural rules and stored decisions."""
    graph_violations = _check_graph_rules(repo_root)
    decision_drifts = _check_decision_drift(repo_root)

    if not graph_violations and not decision_drifts:
        return "No architecture drift detected."

    lines = []
    if graph_violations:
        lines.append(f"# Layer Violations ({len(graph_violations)})\n")
        for v in graph_violations:
            lines.append(f"- ⛔ **{v['rule']}**: `{v['source']}` → `{v['target']}`")
        lines.append("")
    if decision_drifts:
        lines.append(f"# Decision Drift ({len(decision_drifts)})\n")
        for d in decision_drifts:
            lines.append(f"## {d['decision']}")
            for issue in d["issues"]:
                lines.append(f"- ⚠️ {issue}")
            lines.append("")
    lines.append("*Review to confirm if drift is intentional.*")
    return "\n".join(lines)


def _init_rules(repo_root: Path) -> None:
    """Initialize default rules.yaml if not exists."""
    import yaml
    path = mnemo_path(repo_root) / RULES_FILE
    if path.exists():
        return
    default = {"rules": [{"source": "ui", "cannot_access": "database", "description": "UI layer cannot access DB directly"}]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(default, default_flow_style=False), encoding="utf-8")
