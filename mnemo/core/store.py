"""JSONL append-only store — lock-free, crash-tolerant, injection-safe.

The foundation primitive for all persistent storage. Based on gstack's jsonl-store.ts pattern.

Key properties:
- O_APPEND writes: atomic under PIPE_BUF (4096 bytes on macOS/Linux)
- Tolerant reader: skips malformed lines, never crashes
- Injection scanning: rejects instruction-like content at write time
- Single-line enforcement: embedded newlines cause rejection

Usage:
    from mnemo.core.store import append_jsonl, read_jsonl

    append_jsonl(path, {"type": "decide", "decision": "Use PostgreSQL"})
    entries = read_jsonl(path)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from .injection import has_injection

T = TypeVar("T")

# Max record size for PIPE_BUF atomicity (4096 on macOS/Linux, leave margin)
MAX_RECORD_BYTES = 3800


def append_jsonl(path: Path | str, record: dict, *, validate: bool = True) -> None:
    """Append a single JSON record to a JSONL file. Lock-free, atomic under PIPE_BUF.

    Args:
        path: File path to append to. Created if doesn't exist.
        record: Dict to serialize as single-line JSON.
        validate: If True, check for injection patterns and enforce size limits.

    Raises:
        ValueError: If record contains injection patterns, embedded newlines, or exceeds size limit.
    """
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))

    if "\n" in line:
        raise ValueError("Record serialized to multiple lines (embedded newline)")

    if validate:
        # Check size (PIPE_BUF atomicity guarantee)
        if len(line.encode("utf-8")) > MAX_RECORD_BYTES:
            raise ValueError(f"Record exceeds {MAX_RECORD_BYTES} bytes — PIPE_BUF atomicity not guaranteed")

        # Check for injection in any string value
        for value in _extract_strings(record):
            if has_injection(value):
                raise ValueError(f"Record contains injection pattern in value: {value[:50]}")

    # O_APPEND write — atomic for single lines under PIPE_BUF
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_jsonl(path: Path | str) -> list[dict]:
    """Read all records from a JSONL file. Tolerant: skips malformed lines.

    Args:
        path: File path to read from.

    Returns:
        List of parsed records. Empty list if file doesn't exist or is empty.
        Malformed lines are silently skipped (crash-tolerant).
    """
    path = Path(path)
    if not path.exists():
        return []

    records = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    # Malformed line — skip, keep reading (crash-tolerant)
                    continue
    except OSError:
        return []

    return records


def _extract_strings(obj, depth: int = 0) -> list[str]:
    """Recursively extract all string values from a dict/list (max depth 3)."""
    if depth > 3:
        return []
    strings = []
    if isinstance(obj, str):
        strings.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            strings.extend(_extract_strings(v, depth + 1))
    elif isinstance(obj, list):
        for item in obj:
            strings.extend(_extract_strings(item, depth + 1))
    return strings
