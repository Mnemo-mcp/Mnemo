"""Git-backed snapshots for .mnemo state."""
from __future__ import annotations

import shutil
import subprocess  # nosec B404
import time
from pathlib import Path

from ..config import mnemo_path


def _snapshots_dir(repo_root: Path) -> Path:
    return mnemo_path(repo_root) / ".snapshots"


def _run_git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 B607
        ["git"] + list(args), cwd=str(cwd), capture_output=True, text=True, timeout=10
    )


def _ensure_repo(snap_dir: Path) -> None:
    """Init git repo in snapshots dir if not already present."""
    snap_dir.mkdir(parents=True, exist_ok=True)
    if not (snap_dir / ".git").exists():
        _run_git(snap_dir, "init")
        _run_git(snap_dir, "config", "user.email", "mnemo@local")
        _run_git(snap_dir, "config", "user.name", "Mnemo")


def create_snapshot(repo_root: Path) -> str:
    """Copy .mnemo/*.json to .snapshots/ and commit."""
    base = mnemo_path(repo_root)
    snap_dir = _snapshots_dir(repo_root)
    _ensure_repo(snap_dir)

    # Copy all json files
    copied = 0
    for f in base.glob("*.json"):
        shutil.copy2(f, snap_dir / f.name)
        copied += 1

    if copied == 0:
        return "No .json files to snapshot."

    _run_git(snap_dir, "add", "-A")
    msg = f"snapshot {time.strftime('%Y-%m-%d %H:%M:%S')}"
    result = _run_git(snap_dir, "commit", "-m", msg, "--allow-empty")
    if result.returncode != 0 and "nothing to commit" in result.stdout:
        return "No changes since last snapshot."
    return f"Snapshot created: {msg} ({copied} files)"


def list_snapshots(repo_root: Path) -> list[dict]:
    """List all snapshots as [{hash, timestamp, message}]."""
    snap_dir = _snapshots_dir(repo_root)
    if not (snap_dir / ".git").exists():
        return []
    result = _run_git(snap_dir, "log", "--format=%H|%at|%s")
    if result.returncode != 0:
        return []
    snapshots = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            snapshots.append({"hash": parts[0], "timestamp": int(parts[1]), "message": parts[2]})
    return snapshots


def restore_snapshot(repo_root: Path, commit_hash: str) -> str:
    """Restore .mnemo/*.json from a snapshot commit."""
    base = mnemo_path(repo_root)
    snap_dir = _snapshots_dir(repo_root)
    if not (snap_dir / ".git").exists():
        return "No snapshots found."

    result = _run_git(snap_dir, "checkout", commit_hash, "--", ".")
    if result.returncode != 0:
        return f"Failed to restore: {result.stderr.strip()}"

    # Copy restored files back
    restored = 0
    for f in snap_dir.glob("*.json"):
        shutil.copy2(f, base / f.name)
        restored += 1

    # Reset snapshots working tree back to HEAD
    _run_git(snap_dir, "checkout", "HEAD", "--", ".")
    return f"Restored {restored} files from snapshot {commit_hash[:8]}."
