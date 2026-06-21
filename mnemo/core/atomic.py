"""Atomic file operations — tmp+rename for crash-safe writes.

Never corrupts files mid-write. All JSON file mutations go through this module.

Usage:
    from mnemo.core.atomic import atomic_write_json, atomic_read_json

    atomic_write_json(path, data)  # Safe: writes to tmp, then renames
    data = atomic_read_json(path)  # Tolerant: returns [] on missing/corrupt
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_json(path: Path | str, data: Any, *, indent: int = 2) -> None:
    """Write JSON data atomically via tmp file + rename.

    This ensures the file is NEVER in a half-written state.
    If the process crashes mid-write, the original file remains intact.

    Args:
        path: Target file path.
        data: JSON-serializable data.
        indent: JSON indentation (default 2).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file in same directory (same filesystem for atomic rename)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp", prefix=f".{path.stem}_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.write("\n")  # Trailing newline
            f.flush()
            os.fsync(f.fileno())  # Ensure data hits disk
        os.rename(tmp_path, path)  # Atomic on POSIX (same filesystem)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def atomic_read_json(path: Path | str, default: Any = None) -> Any:
    """Read JSON file with graceful fallback.

    Args:
        path: File to read.
        default: Value to return if file doesn't exist or is corrupt. Defaults to [].

    Returns:
        Parsed JSON data, or default on any error.
    """
    if default is None:
        default = []
    path = Path(path)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default
