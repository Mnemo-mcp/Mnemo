"""Audit trail for Mnemo operations."""

from __future__ import annotations
import json
import os
import tempfile
import time
from pathlib import Path

_MAX_ENTRIES = 1000


def record_audit(repo_root: Path, operation: str, target_id: str, target_type: str, details: str = '') -> None:
    """Record an audit entry."""

    audit_path = repo_root / '.mnemo' / 'audit.json'
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    entries = []
    if audit_path.exists():
        try:
            entries = json.loads(audit_path.read_text())
        except (json.JSONDecodeError, OSError):
            entries = []

    entries.append({
        'timestamp': time.time(),
        'operation': operation,
        'target_id': target_id,
        'target_type': target_type,
        'details': details,
    })

    if len(entries) > _MAX_ENTRIES:
        entries = entries[-_MAX_ENTRIES:]

    fd, tmp = tempfile.mkstemp(dir=str(audit_path.parent))
    try:
        os.write(fd, json.dumps(entries, indent=2).encode())
        os.close(fd)
        os.replace(tmp, str(audit_path))
    except Exception:
        os.close(fd) if not os.get_inheritable(fd) else None
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def get_audit_log(repo_root: Path, limit: int = 50) -> list[dict]:
    """Retrieve recent audit entries."""
    audit_path = repo_root / '.mnemo' / 'audit.json'
    if not audit_path.exists():
        return []
    try:
        entries = json.loads(audit_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    return entries[-limit:]
