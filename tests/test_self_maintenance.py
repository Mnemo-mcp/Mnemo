"""MNO-032: Self-maintenance tests — eviction, pinning, consolidation, confidence decay."""

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from mnemo.memory import add_memory, PINNED_CATEGORIES
from mnemo.memory.retention import auto_forget_sweep, compress_memory
from mnemo.memory.services import _maybe_consolidate, _CONSOLIDATION_THRESHOLD
from mnemo.corrections import add_correction
from mnemo.storage import Collections, get_storage


def make_repo(tmp_path):
    d = tmp_path / ".mnemo"
    d.mkdir()
    for f in ("memory.json", "decisions.json", "plans.json", "tasks.json"):
        (d / f).write_text("[]")
    (d / "context.json").write_text("{}")
    (d / "hashes.json").write_text("{}")
    return tmp_path


class TestEvictionRemovesLowRetention:
    def test_over_max_active_triggers_eviction(self, tmp_path):
        repo = make_repo(tmp_path)
        storage = get_storage(repo)
        now = time.time()
        entries = []
        for i in range(250):
            entries.append({
                "id": i + 1,
                "timestamp": now - (100 + i) * 86400,
                "category": "general",
                "content": f"Low value note number {i}",
                "access_count": 0,
                "confidence": 0.5,
                "importance": 2,
            })
        storage.write_collection(Collections.MEMORY, entries)

        auto_forget_sweep(repo)

        entries_after = storage.read_collection(Collections.MEMORY)
        active = [e for e in entries_after if not e.get("evicted")]
        assert len(active) <= 200


class TestPinnedNeverEvicted:
    def test_architecture_and_decision_survive(self, tmp_path):
        repo = make_repo(tmp_path)
        storage = get_storage(repo)
        now = time.time()
        entries = []
        # Add pinned category memories (old, zero access)
        for i, cat in enumerate(["architecture", "decision", "preference"]):
            entries.append({
                "id": i + 1,
                "timestamp": now - 300 * 86400,
                "category": cat,
                "content": f"Important {cat} memory",
                "access_count": 0,
                "confidence": 0.9,
                "importance": 5,
            })
        # Fill with general memories to exceed cap
        for i in range(250):
            entries.append({
                "id": i + 100,
                "timestamp": now - (100 + i) * 86400,
                "category": "general",
                "content": f"Filler note {i}",
                "access_count": 0,
                "confidence": 0.5,
                "importance": 2,
            })
        storage.write_collection(Collections.MEMORY, entries)

        auto_forget_sweep(repo)

        entries_after = storage.read_collection(Collections.MEMORY)
        pinned = [e for e in entries_after if e.get("category") in PINNED_CATEGORIES and not e.get("evicted")]
        assert len(pinned) == 3


class TestConsolidationTriggers:
    def test_maybe_consolidate_runs(self, tmp_path):
        repo = make_repo(tmp_path)
        storage = get_storage(repo)
        now = time.time()
        entries = []
        for i in range(100):
            entries.append({
                "id": i + 1,
                "timestamp": now - (60 + i) * 86400,
                "category": "bug",
                "content": f"Fixed null pointer in handler service {i}",
                "access_count": 0,
                "confidence": 0.8,
                "recall_count": 0,
                "last_recalled": None,
                "tier": "session",
            })
        storage.write_collection(Collections.MEMORY, entries)

        import mnemo.memory.services as svc
        svc._last_consolidation = 0  # Reset cooldown

        _maybe_consolidate(repo)

        entries_after = storage.read_collection(Collections.MEMORY)
        assert len(entries_after) < 100


class TestConfidenceDecayOnCorrection:
    def test_correction_decays_matching_memory(self, tmp_path):
        repo = make_repo(tmp_path)
        with patch("mnemo.memory._get_current_branch", return_value="main"):
            entry = add_memory(repo, "Use Redis for session caching", "architecture")

        original_confidence = entry["confidence"]

        add_correction(
            repo,
            suggestion="Use Redis for session caching",
            correction="Use Memcached for session caching",
            context="session caching Redis",
        )

        storage = get_storage(repo)
        entries = storage.read_collection(Collections.MEMORY)
        updated = next(e for e in entries if e["id"] == entry["id"])
        assert updated["confidence"] < original_confidence
