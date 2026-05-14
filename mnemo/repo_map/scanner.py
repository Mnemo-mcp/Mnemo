"""File discovery: hashing, ignore logic, change detection."""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..config import SUPPORTED_EXTENSIONS, mnemo_path, should_ignore
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
    """Quick check if any files changed since last map generation using mtime."""
    summary_path = mnemo_path(repo_root) / "summary.md"
    if not summary_path.exists():
        return True
    last_map_time = summary_path.stat().st_mtime

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
