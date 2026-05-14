"""Tests for mnemo/snapshot.py — git-backed snapshots."""
import json
import pytest
from unittest.mock import patch
from mnemo.persistence.snapshot import create_snapshot, list_snapshots, restore_snapshot


@pytest.fixture
def repo(tmp_path):
    mnemo_dir = tmp_path / ".mnemo"
    mnemo_dir.mkdir()
    with patch("mnemo.persistence.snapshot.mnemo_path", return_value=mnemo_dir):
        yield tmp_path


def test_create_snapshot_creates_snapshots_dir(repo):
    # Write a json file so there's something to snapshot
    (repo / ".mnemo" / "memory.json").write_text("[]")
    with patch("mnemo.persistence.snapshot.mnemo_path", return_value=repo / ".mnemo"):
        result = create_snapshot(repo)
    snap_dir = repo / ".mnemo" / ".snapshots"
    assert snap_dir.exists()
    assert "Snapshot created" in result


def test_list_snapshots_returns_entries(repo):
    (repo / ".mnemo" / "memory.json").write_text("[]")
    with patch("mnemo.persistence.snapshot.mnemo_path", return_value=repo / ".mnemo"):
        create_snapshot(repo)
        snapshots = list_snapshots(repo)
    assert len(snapshots) >= 1
    assert "hash" in snapshots[0]
    assert "timestamp" in snapshots[0]
    assert "message" in snapshots[0]


def test_restore_snapshot_restores_files(repo):
    mnemo_dir = repo / ".mnemo"
    # Create initial state and snapshot
    (mnemo_dir / "memory.json").write_text(json.dumps([{"id": 1}]))
    with patch("mnemo.persistence.snapshot.mnemo_path", return_value=mnemo_dir):
        create_snapshot(repo)
        snapshots = list_snapshots(repo)
        commit_hash = snapshots[0]["hash"]

        # Modify the file
        (mnemo_dir / "memory.json").write_text(json.dumps([{"id": 2}]))

        # Restore
        result = restore_snapshot(repo, commit_hash)
    assert "Restored" in result
    restored = json.loads((mnemo_dir / "memory.json").read_text())
    assert restored == [{"id": 1}]
