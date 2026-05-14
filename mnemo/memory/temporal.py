"""Temporal Intelligence — track evolution and instability over time (MNO-844/845)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ..config import mnemo_path

TEMPORAL_FILE = "temporal.json"


def _load_temporal(repo_root: Path) -> dict[str, Any]:
    path = mnemo_path(repo_root) / TEMPORAL_FILE
    if not path.exists():
        return {"nodes": {}, "snapshots": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"nodes": {}, "snapshots": []}


def _save_temporal(repo_root: Path, data: dict[str, Any]) -> None:
    path = mnemo_path(repo_root) / TEMPORAL_FILE
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def record_changes(repo_root: Path, changed_files: list[str]) -> int:
    """Record file changes and update node change_count + last_modified."""
    data = _load_temporal(repo_root)
    nodes = data.setdefault("nodes", {})
    now = time.time()
    updated = 0

    for filepath in changed_files:
        node_id = f"file:{filepath}"
        if node_id not in nodes:
            nodes[node_id] = {"change_count": 0, "first_seen": now, "last_modified": now}
        nodes[node_id]["change_count"] = nodes[node_id].get("change_count", 0) + 1
        nodes[node_id]["last_modified"] = now
        updated += 1

    # Record snapshot
    data.setdefault("snapshots", []).append({
        "timestamp": now,
        "files_changed": len(changed_files),
    })
    # Keep only last 100 snapshots
    data["snapshots"] = data["snapshots"][-100:]

    _save_temporal(repo_root, data)
    return updated


def get_instability_scores(repo_root: Path, top_n: int = 10) -> list[dict[str, Any]]:
    """Calculate instability score per file (change_count / age_days). MNO-845."""
    data = _load_temporal(repo_root)
    nodes = data.get("nodes", {})
    now = time.time()

    scores = []
    for node_id, info in nodes.items():
        age_days = max((now - info.get("first_seen", now)) / 86400, 1)
        change_count = info.get("change_count", 0)
        instability = round(change_count / age_days, 3)
        scores.append({
            "file": node_id.replace("file:", ""),
            "change_count": change_count,
            "age_days": round(age_days, 1),
            "instability": instability,
            "last_modified": info.get("last_modified"),
        })

    scores.sort(key=lambda x: x["instability"], reverse=True)
    return scores[:top_n]


def format_temporal_report(repo_root: Path) -> str:
    """Format temporal intelligence as markdown."""
    scores = get_instability_scores(repo_root)
    if not scores:
        return "No temporal data yet. Changes will be tracked on next `mnemo map` run."

    lines = ["# Temporal Intelligence — Instability Report\n"]
    lines.append("| File | Changes | Age (days) | Instability |")
    lines.append("|------|---------|-----------|-------------|")
    for s in scores:
        lines.append(f"| `{s['file']}` | {s['change_count']} | {s['age_days']} | {s['instability']} |")

    hotspots = [s for s in scores if s["instability"] > 1.0]
    if hotspots:
        lines.append(f"\n⚠️ **{len(hotspots)} hotspots** with instability > 1.0 (more than 1 change/day)")

    return "\n".join(lines)
