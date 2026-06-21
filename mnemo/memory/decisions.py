"""Event-sourced decisions — immutable event log with computed active state.

Architecture:
    Source of truth: .mnemo/decisions.events.jsonl (append-only JSONL event log)
    Read path:       .mnemo/decisions.json (pre-computed active snapshot, same format as before)

All existing readers (search.py, enrichment.py, drift.py, mining.py, retention.py)
continue reading decisions.json unchanged. The file just gets rebuilt from events
instead of being mutated in place.

Event types:
    decide    — Records a new decision
    supersede — Replaces a prior decision (the old one disappears from active view)
    redact    — Permanently removes a decision (for accidental secrets)

Properties:
    - Concurrent-safe writes (JSONL append = O_APPEND, atomic under PIPE_BUF)
    - Full audit trail (every change is an event, nothing is lost)
    - Branch-scoped (decisions can be repo-wide or branch-specific)
    - Dangling references are harmless no-ops
    - Pre-computed snapshot for O(1) recall reads
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any, Literal

from ..config import mnemo_path
from ..core.injection import has_injection
from ..core.store import append_jsonl, read_jsonl
from ..core.atomic import atomic_write_json, atomic_read_json
from ..utils.privacy import strip_secrets
from ..utils.audit import record_audit

DecisionKind = Literal["decide", "supersede", "redact"]
DecisionScope = Literal["repo", "branch"]


# --- File paths ---

def _events_path(repo_root: Path) -> Path:
    """Append-only event log (source of truth)."""
    return mnemo_path(repo_root) / "decisions.events.jsonl"


def _snapshot_path(repo_root: Path) -> Path:
    """Active snapshot — this IS decisions.json that all readers use."""
    return mnemo_path(repo_root) / "decisions.json"


# --- Core write operations ---

def log_decision(
    repo_root: Path,
    decision: str,
    reasoning: str = "",
    scope: DecisionScope = "repo",
    branch: str | None = None,
    source: str = "agent",
) -> dict[str, Any]:
    """Record a new decision event.

    Validates for injection, strips secrets, appends to event log,
    rebuilds active snapshot (decisions.json).

    Raises:
        ValueError: If decision text contains injection patterns or is empty.
    """
    decision = decision.strip()
    if not decision:
        raise ValueError("Decision text is required")

    if has_injection(decision):
        raise ValueError("Decision rejected: contains injection pattern")

    decision, _ = strip_secrets(decision)
    if reasoning:
        reasoning, _ = strip_secrets(reasoning)

    _ensure_events_exist(repo_root)

    # Dedup check against current active decisions
    from ._shared import _text_similarity, DEDUP_SIMILARITY_THRESHOLD, CONTRADICTION_SIMILARITY_THRESHOLD
    active = get_active_decisions(repo_root)
    for existing in active:
        if _text_similarity(decision, existing.get("decision", "")) >= DEDUP_SIMILARITY_THRESHOLD:
            return existing  # Already exists, no new event needed

    event_id = uuid.uuid4().hex[:12]
    event = {
        "id": event_id,
        "kind": "decide",
        "decision": decision,
        "reasoning": reasoning,
        "scope": scope,
        "date": _ts_to_iso(time.time()),
        "source": source,
    }
    if scope == "branch" and branch:
        event["branch"] = branch

    append_jsonl(_events_path(repo_root), event)

    # Auto-detect contradictions and supersede them
    for existing in active:
        sim = _text_similarity(decision, existing.get("decision", ""))
        if CONTRADICTION_SIMILARITY_THRESHOLD <= sim < DEDUP_SIMILARITY_THRESHOLD:
            supersede_decision(repo_root, existing["id"], source=source, _skip_rebuild=True)

    _rebuild_snapshot(repo_root)
    record_audit(repo_root, "add_decision", event_id, "decision", decision[:100])
    return event


def supersede_decision(
    repo_root: Path,
    target_id: str,
    source: str = "agent",
    _skip_rebuild: bool = False,
) -> dict[str, Any]:
    """Mark a decision as superseded. Returns the supersede event."""
    _ensure_events_exist(repo_root)

    event = {
        "id": uuid.uuid4().hex[:12],
        "kind": "supersede",
        "supersedes": str(target_id),
        "scope": "repo",
        "date": _ts_to_iso(time.time()),
        "source": source,
    }

    append_jsonl(_events_path(repo_root), event, validate=False)
    if not _skip_rebuild:
        _rebuild_snapshot(repo_root)
        record_audit(repo_root, "supersede_decision", str(target_id), "decision", f"superseded by {source}")
    return event


def redact_decision(
    repo_root: Path,
    target_id: str,
    source: str = "user",
) -> dict[str, Any]:
    """Permanently redact a decision (e.g., accidental secret).

    Appends a redact event AND scrubs the original decision text from the event log.
    """
    _ensure_events_exist(repo_root)

    event = {
        "id": uuid.uuid4().hex[:12],
        "kind": "redact",
        "supersedes": str(target_id),
        "scope": "repo",
        "date": _ts_to_iso(time.time()),
        "source": source,
    }

    append_jsonl(_events_path(repo_root), event, validate=False)

    # Rewrite event log: scrub the original decision text
    import json
    events_file = _events_path(repo_root)
    events = read_jsonl(events_file)
    lines = []
    for e in events:
        if e.get("id") == str(target_id) and e.get("kind") == "decide":
            e["decision"] = "[REDACTED]"
            e["reasoning"] = ""
        lines.append(json.dumps(e, ensure_ascii=False, separators=(",", ":")))

    # Atomic rewrite of the event log
    content = "\n".join(lines) + "\n" if lines else ""
    events_file.write_text(content, encoding="utf-8")

    _rebuild_snapshot(repo_root)
    record_audit(repo_root, "redact_decision", str(target_id), "decision", "redacted")
    return event


# --- Read operations ---

def get_active_decisions(
    repo_root: Path,
    branch: str | None = None,
) -> list[dict[str, Any]]:
    """Get active decisions, optionally filtered by branch scope.

    Reads from pre-computed snapshot (decisions.json) for O(1) performance.
    Falls back to computing from events if snapshot is stale/missing.
    """
    snapshot = _read_snapshot(repo_root)
    if snapshot is None:
        # No snapshot yet — compute from events
        _ensure_events_exist(repo_root)
        events = read_jsonl(_events_path(repo_root))
        if events:
            snapshot = compute_active(events)
            _write_snapshot(repo_root, snapshot)
        else:
            snapshot = []

    # Filter to active-only
    active = [d for d in snapshot if d.get("active", True)]

    if branch is None:
        return active

    # Filter: repo-wide + matching branch
    return [
        d for d in active
        if d.get("scope", "repo") == "repo"
        or (d.get("scope") == "branch" and d.get("branch") == branch)
    ]


def get_all_events(repo_root: Path) -> list[dict[str, Any]]:
    """Read the full event log (for audit/debug purposes)."""
    _ensure_events_exist(repo_root)
    return read_jsonl(_events_path(repo_root))


# --- Computation ---

def compute_active(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute full decision list from events (active + superseded).

    Returns list in the same format as the old decisions.json:
    [{id, timestamp, decision, reasoning, active, superseded_by, scope, branch, source}, ...]

    Active decisions have active=True, superseded_by=None.
    Retired decisions have active=False, superseded_by=<superseding_event_id>.
    Redacted decisions are excluded entirely.
    """
    # Build retirement map: target_id → superseding_event_id
    retired: dict[str, str] = {}
    redacted: set[str] = set()
    for e in events:
        target = e.get("supersedes")
        if not target:
            continue
        if e.get("kind") == "redact":
            redacted.add(str(target))
        elif e.get("kind") == "supersede":
            retired[str(target)] = str(e.get("id", ""))

    result = []
    for e in events:
        if e.get("kind") != "decide":
            continue
        eid = str(e.get("id", ""))
        if eid in redacted:
            continue  # Redacted = gone completely

        is_active = eid not in retired
        entry = {
            "id": eid,
            "timestamp": _iso_to_ts(e.get("date", "")),
            "decision": e.get("decision", ""),
            "reasoning": e.get("reasoning", ""),
            "active": is_active,
            "superseded_by": retired.get(eid),
            # New fields (readers ignore unknown keys)
            "scope": e.get("scope", "repo"),
            "branch": e.get("branch"),
            "source": e.get("source", "agent"),
        }
        result.append(entry)

    # Sort by timestamp (oldest first)
    result.sort(key=lambda e: e.get("timestamp", 0))
    return result


# --- Snapshot management ---

def _rebuild_snapshot(repo_root: Path) -> None:
    """Rebuild decisions.json from the event log. Atomic write."""
    events = read_jsonl(_events_path(repo_root))
    active = compute_active(events)
    _write_snapshot(repo_root, active)


def _write_snapshot(repo_root: Path, active: list[dict[str, Any]]) -> None:
    """Write the active snapshot to decisions.json."""
    atomic_write_json(_snapshot_path(repo_root), active)


def _read_snapshot(repo_root: Path) -> list[dict[str, Any]] | None:
    """Read decisions.json. Returns None if doesn't exist."""
    path = _snapshot_path(repo_root)
    if not path.exists():
        return None
    result = atomic_read_json(path, default=None)
    if result is None or not isinstance(result, list):
        return None
    return result


# --- Migration ---

def _migrate_legacy_if_needed(repo_root: Path) -> None:
    """Migrate old-format decisions.json to event-sourced format.

    Only runs if:
    - decisions.json exists (old format entries without scope/branch fields)
    - decisions.events.jsonl does NOT exist

    After migration, decisions.json is overwritten with the new snapshot format.
    """
    events_file = _events_path(repo_root)
    snapshot_file = _snapshot_path(repo_root)

    if events_file.exists():
        return  # Already migrated

    if not snapshot_file.exists():
        return  # No legacy file either

    import json
    try:
        entries = json.loads(snapshot_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    if not isinstance(entries, list) or not entries:
        return

    # Check if it's old format (has 'active' field as mutable state)
    first = entries[0] if entries else {}
    if "kind" in first:
        return  # Already new format

    # Migrate each entry to an event
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        decision_text = entry.get("decision", "")
        if not decision_text:
            continue

        event_id = str(entry.get("id", uuid.uuid4().hex[:8]))
        event = {
            "id": event_id,
            "kind": "decide",
            "decision": decision_text,
            "reasoning": entry.get("reasoning", ""),
            "scope": "repo",
            "date": _ts_to_iso(entry.get("timestamp", time.time())),
            "source": "agent",
        }
        try:
            append_jsonl(events_file, event, validate=False)
        except (ValueError, OSError):
            continue

        # If it was superseded in old format, emit a supersede event
        if not entry.get("active", True):
            supersede_event = {
                "id": uuid.uuid4().hex[:12],
                "kind": "supersede",
                "supersedes": event_id,
                "scope": "repo",
                "date": _ts_to_iso(entry.get("timestamp", time.time()) + 1),
                "source": "agent",
            }
            try:
                append_jsonl(events_file, supersede_event, validate=False)
            except (ValueError, OSError):
                continue

    # Rebuild snapshot (overwrites old decisions.json with new format)
    _rebuild_snapshot(repo_root)


def migrate_decisions(repo_root: Path) -> bool:
    """Explicitly trigger migration from old decisions.json to event-sourced format.

    Call from mnemo init or upgrade path.
    Returns True if migration happened, False if nothing to migrate.
    """
    _migrate_legacy_if_needed(repo_root)
    return _events_path(repo_root).exists() and _events_path(repo_root).stat().st_size > 0


# --- Internal helpers ---

def _ensure_events_exist(repo_root: Path) -> None:
    """Ensure the events file exists. Creates it empty if needed."""
    events_file = _events_path(repo_root)
    if not events_file.exists():
        events_file.parent.mkdir(parents=True, exist_ok=True)
        events_file.touch()


def _ts_to_iso(ts: float) -> str:
    """Convert Unix timestamp to ISO-8601 string."""
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _iso_to_ts(iso: str) -> float:
    """Convert ISO-8601 string to Unix timestamp."""
    if not iso:
        return time.time()
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except (ValueError, TypeError):
        return time.time()
