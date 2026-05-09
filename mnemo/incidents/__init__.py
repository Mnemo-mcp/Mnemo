"""Incident memory - store production incidents, root cause, fix, and prevention."""

from __future__ import annotations

import time
from pathlib import Path

from ..storage import Collections, get_storage


def _load_incidents(repo_root: Path) -> list[dict]:
    data = get_storage(repo_root).read_collection(Collections.INCIDENTS)
    return data if isinstance(data, list) else []


def _save_incidents(repo_root: Path, incidents: list[dict]) -> None:
    get_storage(repo_root).write_collection(Collections.INCIDENTS, incidents)


def add_incident(
    repo_root: Path,
    title: str,
    what_happened: str,
    root_cause: str,
    fix: str,
    prevention: str = "",
    severity: str = "medium",
    services: list[str] | None = None,
) -> dict:
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

    matches = [
        incident
        for incident in incidents
        if query_lower in incident.get("title", "").lower()
        or query_lower in incident.get("root_cause", "").lower()
        or query_lower in incident.get("what_happened", "").lower()
        or any(query_lower in service.lower() for service in incident.get("services", []))
    ]

    if not matches:
        return f"No incidents matching '{query}'."

    lines = [f"# Incidents matching '{query}'\n"]
    for incident in matches:
        severity = f"[{incident['severity']}]" if incident.get("severity") else ""
        lines.append(f"## {incident['title']} {severity}")
        lines.append(f"**What happened:** {incident['what_happened']}")
        lines.append(f"**Root cause:** {incident['root_cause']}")
        lines.append(f"**Fix:** {incident['fix']}")
        if incident.get("prevention"):
            lines.append(f"**Prevention:** {incident['prevention']}")
        if incident.get("services"):
            lines.append(f"**Services affected:** {', '.join(incident['services'])}")
        lines.append("")
    return "\n".join(lines)


def format_incidents(repo_root: Path) -> str:
    """Format all incidents as markdown."""
    incidents = _load_incidents(repo_root)
    if not incidents:
        return "No incidents recorded."

    lines = ["# Incident History\n"]
    for incident in incidents:
        severity = f"[{incident['severity']}]" if incident.get("severity") else ""
        lines.append(f"- {severity} **{incident['title']}** - {incident['root_cause'][:80]}")
    return "\n".join(lines)
