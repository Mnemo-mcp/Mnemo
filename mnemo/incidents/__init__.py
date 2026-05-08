"""Incident Memory — store production incidents, root cause, fix, prevention."""

from __future__ import annotations

import json
import time
from pathlib import Path

from ..config import mnemo_path

INCIDENTS_FILE = "incidents.json"


def _incidents_path(repo_root: Path) -> Path:
    return mnemo_path(repo_root) / INCIDENTS_FILE


def _load_incidents(repo_root: Path) -> list[dict]:
    path = _incidents_path(repo_root)
    if path.exists():
        return json.loads(path.read_text())
    return []


def _save_incidents(repo_root: Path, incidents: list[dict]):
    _incidents_path(repo_root).write_text(json.dumps(incidents, indent=2))


def add_incident(repo_root: Path, title: str, what_happened: str,
                 root_cause: str, fix: str, prevention: str = "",
                 severity: str = "medium", services: list[str] = None) -> dict:
    """Store a production incident."""
    incidents = _load_incidents(repo_root)
    entry = {
        "id": len(incidents) + 1,
        "timestamp": time.time(),
        "title": title,
        "what_happened": what_happened,
        "root_cause": root_cause,
        "fix": fix,
        "prevention": prevention,
        "severity": severity,
        "services": services or [],
    }
    incidents.append(entry)
    _save_incidents(repo_root, incidents)
    return entry


def search_incidents(repo_root: Path, query: str) -> str:
    """Search incident history."""
    incidents = _load_incidents(repo_root)
    query_lower = query.lower()

    matches = [i for i in incidents if
               query_lower in i.get("title", "").lower() or
               query_lower in i.get("root_cause", "").lower() or
               query_lower in i.get("what_happened", "").lower() or
               any(query_lower in s.lower() for s in i.get("services", []))]

    if not matches:
        return f"No incidents matching '{query}'."

    lines = [f"# Incidents matching '{query}'\n"]
    for i in matches:
        sev = f"[{i['severity']}]" if i.get("severity") else ""
        lines.append(f"## {i['title']} {sev}")
        lines.append(f"**What happened:** {i['what_happened']}")
        lines.append(f"**Root cause:** {i['root_cause']}")
        lines.append(f"**Fix:** {i['fix']}")
        if i.get("prevention"):
            lines.append(f"**Prevention:** {i['prevention']}")
        if i.get("services"):
            lines.append(f"**Services affected:** {', '.join(i['services'])}")
        lines.append("")
    return "\n".join(lines)


def format_incidents(repo_root: Path) -> str:
    """Format all incidents as markdown."""
    incidents = _load_incidents(repo_root)
    if not incidents:
        return "No incidents recorded."

    lines = ["# Incident History\n"]
    for i in incidents:
        sev = f"[{i['severity']}]" if i.get("severity") else ""
        lines.append(f"- {sev} **{i['title']}** — {i['root_cause'][:80]}")
    return "\n".join(lines)
