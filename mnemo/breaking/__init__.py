"""Breaking change detector — compares current graph symbols against baseline."""

from __future__ import annotations

import json
import time
from pathlib import Path

from ..config import mnemo_path

BASELINE_FILE = "api_baseline.json"


def _load_baseline(repo_root: Path) -> dict:
    path = mnemo_path(repo_root) / BASELINE_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_baseline(repo_root: Path, baseline: dict) -> None:
    path = mnemo_path(repo_root) / BASELINE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")


def _extract_public_api(repo_root: Path) -> dict[str, list[str]]:
    """Extract public API signatures from engine graph."""
    from ..engine.db import open_db, get_db_path

    if not get_db_path(repo_root).exists():
        return {}

    _, conn = open_db(repo_root)
    api: dict[str, list[str]] = {}

    # Classes with their implements
    result = conn.execute("""
        MATCH (c:Class)
        WHERE NOT c.file CONTAINS 'test' AND NOT c.name STARTS WITH '_'
        RETURN c.name, c.file, c.implements
    """)
    while result.has_next():
        row = result.get_next()
        impl = f" : {row[2]}" if row[2] else ""
        api.setdefault(row[1], []).append(f"class {row[0]}{impl}")

    # Functions with signatures
    result = conn.execute("""
        MATCH (f:Function)
        WHERE NOT f.file CONTAINS 'test' AND NOT f.name STARTS WITH '_'
        RETURN f.name, f.file, f.signature
    """)
    while result.has_next():
        row = result.get_next()
        sig = row[2] or row[0]
        api.setdefault(row[1], []).append(sig)

    return api


def save_baseline(repo_root: Path) -> str:
    """Snapshot current public API as the baseline."""
    api = _extract_public_api(repo_root)
    baseline = {"timestamp": time.time(), "api": api}
    _save_baseline(repo_root, baseline)
    total = sum(len(v) for v in api.values())
    return f"Baseline saved: {len(api)} files, {total} public symbols."


def detect_breaking_changes(repo_root: Path) -> str:
    """Compare current API against saved baseline."""
    baseline = _load_baseline(repo_root)
    if not baseline or not baseline.get("api"):
        return "No API baseline found. Save a baseline first with action='baseline'."

    old_api = baseline["api"]
    new_api = _extract_public_api(repo_root)

    removed_files = []
    removed_symbols = []
    changed_symbols = []

    for file, old_sigs in old_api.items():
        if file not in new_api:
            removed_files.append(file)
            continue
        new_sigs = new_api[file]
        new_names = {s.split("(")[0].strip() for s in new_sigs}
        for sig in old_sigs:
            old_name = sig.split("(")[0].strip()
            if old_name not in new_names:
                removed_symbols.append({"file": file, "symbol": sig})
            elif sig not in new_sigs:
                new_sig = next((s for s in new_sigs if s.split("(")[0].strip() == old_name), "?")
                changed_symbols.append({"file": file, "old": sig, "new": new_sig})

    if not removed_files and not removed_symbols and not changed_symbols:
        return "No breaking changes detected against baseline."

    lines = ["# Breaking Changes Detected\n"]
    if removed_files:
        lines.append(f"## Removed Files ({len(removed_files)})\n")
        for f in removed_files[:20]:
            lines.append(f"- ❌ `{f}`")
        lines.append("")
    if removed_symbols:
        lines.append(f"## Removed Symbols ({len(removed_symbols)})\n")
        for s in removed_symbols[:30]:
            lines.append(f"- ❌ `{s['file']}`: `{s['symbol']}`")
        lines.append("")
    if changed_symbols:
        lines.append(f"## Changed Signatures ({len(changed_symbols)})\n")
        for s in changed_symbols[:30]:
            lines.append(f"- ⚠️ `{s['file']}`: `{s['old']}` → `{s['new']}`")
        lines.append("")
    return "\n".join(lines)
