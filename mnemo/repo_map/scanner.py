"""File discovery: hashing, ignore logic, change detection."""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..config import SUPPORTED_EXTENSIONS, should_ignore
from ..storage import Collections, get_storage

CHANGELOG_FILE = "changelog.json"
HASH_INDEX_FILE = "hashes.json"
MAX_FILE_SIZE = 100_000


def _should_ignore(path: Path) -> bool:
    return should_ignore(path)


def _file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()


def _load_hashes(repo_root: Path) -> dict[str, str]:
    data = get_storage(repo_root).read_collection(Collections.HASHES)
    if not isinstance(data, dict):
        return {}
    return {str(path): str(file_hash) for path, file_hash in data.items()}


def _save_hashes(repo_root: Path, hashes: dict[str, str]):
    get_storage(repo_root).write_collection(Collections.HASHES, hashes)


def has_changes(repo_root: Path) -> bool:
    """Quick check if any files changed or were deleted since last map generation."""
    from ..config import mnemo_path as _mnemo_path
    summary_path = _mnemo_path(repo_root) / "summary.md"
    if not summary_path.exists():
        return True
    last_map_time = summary_path.stat().st_mtime

    # Check for deleted files: compare stored hash count vs current file count
    hashes_path = _mnemo_path(repo_root) / "hashes.json"
    if hashes_path.exists():
        import json
        try:
            stored_hashes = json.loads(hashes_path.read_text())
            stored_count = len(stored_hashes) if isinstance(stored_hashes, dict) else 0
        except (json.JSONDecodeError, OSError):
            stored_count = 0

        current_count = 0
        for ext in SUPPORTED_EXTENSIONS:
            for filepath in repo_root.rglob(f"*{ext}"):
                if _should_ignore(filepath) or filepath.stat().st_size > MAX_FILE_SIZE:
                    continue
                current_count += 1

        # If file count changed significantly (files added or deleted), rebuild
        if abs(current_count - stored_count) > 0:
            return True

    # Check for modified files
    for ext in SUPPORTED_EXTENSIONS:
        for filepath in repo_root.rglob(f"*{ext}"):
            if _should_ignore(filepath) or filepath.stat().st_size > MAX_FILE_SIZE:
                continue
            try:
                if filepath.stat().st_mtime > last_map_time:
                    return True
            except OSError:
                continue
    return False
