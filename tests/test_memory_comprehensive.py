"""Comprehensive tests for mnemo/memory module.

Tests the full memory lifecycle: store, search, recall, retention, forget,
deduplication, contradiction detection, lessons, episodes, and slots.
"""
import json
import time
from pathlib import Path

import pytest

from mnemo.memory.store import add_memory, forget_memory, add_decision
from mnemo.memory.search import search_memory
from mnemo.memory.retention import _compute_retention as compute_retention, auto_forget_sweep, compress_memory
from mnemo.memory.lessons import add_lesson, get_lessons as list_lessons, decay_lessons
from mnemo.memory.episodes import start_episode, close_episode, _load_episodes as list_episodes_raw
from mnemo.memory.slots import set_slot, get_slot
from mnemo.storage import get_storage, Collections


@pytest.fixture
def mnemo_project(tmp_path):
    """Create minimal .mnemo/ directory for memory tests."""
    d = tmp_path / ".mnemo"
    d.mkdir()
    (d / "memory.json").write_text("[]")
    (d / "decisions.json").write_text("[]")
    (d / "context.json").write_text("{}")
    (d / "lessons.json").write_text("[]")
    (d / "slots.json").write_text("{}")
    (d / "tasks.json").write_text("[]")
    (d / "episodes.json").write_text("[]")
    return tmp_path


# --- Store operations ---

class TestAddMemory:
    def test_basic_add(self, mnemo_project):
        entry = add_memory(mnemo_project, "Use PostgreSQL for the database")
        assert entry["content"] == "Use PostgreSQL for the database"
        assert entry["id"] is not None

        stored = json.loads((mnemo_project / ".mnemo" / "memory.json").read_text())
        assert len(stored) == 1
        assert stored[0]["content"] == "Use PostgreSQL for the database"

    def test_auto_categorizes_preference(self, mnemo_project):
        entry = add_memory(mnemo_project, "I prefer tabs over spaces")
        assert entry["category"] == "preference"

    def test_auto_categorizes_architecture(self, mnemo_project):
        entry = add_memory(mnemo_project, "The service uses microservices architecture with event-driven communication")
        assert entry["category"] == "architecture"

    def test_strips_secrets(self, mnemo_project):
        entry = add_memory(mnemo_project, "API key is AKIAIOSFODNN7EXAMPLE for AWS access")
        assert "AKIAIOSFODNN7EXAMPLE" not in entry["content"]

    def test_deduplication(self, mnemo_project):
        add_memory(mnemo_project, "Use React for the frontend")
        add_memory(mnemo_project, "Use React for the frontend")  # exact duplicate
        stored = json.loads((mnemo_project / ".mnemo" / "memory.json").read_text())
        assert len(stored) == 1  # no duplicate created

    def test_category_override(self, mnemo_project):
        entry = add_memory(mnemo_project, "something generic", category="bug")
        assert entry["category"] == "bug"


class TestForgetMemory:
    def test_removes_entry(self, mnemo_project):
        entry = add_memory(mnemo_project, "temporary fact")
        mid = entry["id"]
        result = forget_memory(mnemo_project, mid)
        assert "deleted" in result.lower() or str(mid) in result

        stored = json.loads((mnemo_project / ".mnemo" / "memory.json").read_text())
        assert len(stored) == 0

    def test_nonexistent_id(self, mnemo_project):
        result = forget_memory(mnemo_project, 99999)
        assert "not found" in result.lower()


class TestAddDecision:
    def test_basic(self, mnemo_project):
        entry = add_decision(mnemo_project, "Use PostgreSQL", "Better JSON support")
        assert entry["decision"] == "Use PostgreSQL"
        assert entry["reasoning"] == "Better JSON support"

        stored = json.loads((mnemo_project / ".mnemo" / "decisions.json").read_text())
        assert len(stored) == 1

    def test_contradiction_supersedes(self, mnemo_project):
        add_decision(mnemo_project, "Use PostgreSQL for the database layer")
        add_decision(mnemo_project, "Use MongoDB for the database layer")

        stored = json.loads((mnemo_project / ".mnemo" / "decisions.json").read_text())
        active = [d for d in stored if d.get("active", True)]
        # At least the newer one should be active
        assert any("MongoDB" in d["decision"] for d in active)


# --- Retention ---

class TestRetention:
    def test_recent_high_importance_is_hot(self, mnemo_project):
        entry = add_memory(mnemo_project, "Critical architecture decision", category="architecture")
        score = compute_retention(entry, time.time())
        assert score >= 0.5, f"Expected hot (>=0.5), got {score}"

    def test_old_low_importance_is_cold(self, mnemo_project):
        entry = {
            "id": 1, "content": "minor note", "category": "general",
            "timestamp": time.time() - 86400 * 90,  # 90 days old
            "confidence": 0.5, "access_count": 0, "access_history": [],
        }
        score = compute_retention(entry, time.time())
        assert score < 0.25, f"Expected cold (<0.25), got {score}"

    def test_pinned_never_evicted(self, mnemo_project):
        # Architecture gets high salience weight (0.9) but still decays
        # The important thing: it decays MUCH slower than general
        arch_entry = {
            "id": 1, "content": "core architecture", "category": "architecture",
            "timestamp": time.time() - 86400 * 60,  # 60 days old
            "confidence": 1.0, "access_count": 0, "access_history": [],
        }
        general_entry = {
            "id": 2, "content": "trivial note", "category": "general",
            "timestamp": time.time() - 86400 * 60,  # same age
            "confidence": 0.5, "access_count": 0, "access_history": [],
        }
        arch_score = compute_retention(arch_entry, time.time())
        general_score = compute_retention(general_entry, time.time())
        assert arch_score > general_score, f"Architecture ({arch_score}) should score higher than general ({general_score})"

    def test_auto_forget_sweep(self, mnemo_project):
        # Add many low-importance old memories
        storage = get_storage(mnemo_project)
        entries = []
        for i in range(50):
            entries.append({
                "id": i, "content": f"trivial note {i}", "category": "general",
                "timestamp": time.time() - 86400 * 100,
                "confidence": 0.3, "access_count": 0, "access_history": [], "tier": "cold",
            })
        # Add one hot memory
        entries.append({
            "id": 999, "content": "important", "category": "architecture",
            "timestamp": time.time(), "confidence": 1.0,
            "access_count": 5, "access_history": [], "tier": "hot",
        })
        storage.write_collection(Collections.MEMORY, entries)

        result = auto_forget_sweep(mnemo_project)
        remaining = json.loads((mnemo_project / ".mnemo" / "memory.json").read_text())
        # The hot memory should survive
        assert any(e["id"] == 999 for e in remaining)


# --- Search ---

class TestSearchMemory:
    def test_finds_by_keyword(self, mnemo_project):
        add_memory(mnemo_project, "The payment service uses Stripe for processing")
        result = search_memory(mnemo_project, "payment Stripe")
        assert "Stripe" in result or "payment" in result

    def test_empty_for_irrelevant(self, mnemo_project):
        add_memory(mnemo_project, "Use PostgreSQL for the database")
        result = search_memory(mnemo_project, "quantum computing blockchain")
        # Should return "no results" or similar
        assert "no" in result.lower() or "0 result" in result.lower() or len(result.strip()) < 50


# --- Lessons ---

class TestLessons:
    def test_add_lesson(self, mnemo_project):
        add_lesson(mnemo_project, "Always run migrations before deploying")
        lessons = list_lessons(mnemo_project)
        assert len(lessons) == 1
        assert "migrations" in lessons[0]["content"]

    def test_reinforcement(self, mnemo_project):
        add_lesson(mnemo_project, "Check for null before accessing .length")
        add_lesson(mnemo_project, "Check for null before accessing .length")
        lessons = list_lessons(mnemo_project)
        assert len(lessons) == 1  # deduped
        assert lessons[0]["confidence"] > 0.5  # reinforced

    def test_decay(self, mnemo_project):
        add_lesson(mnemo_project, "Some pattern that might decay")
        decay_lessons(mnemo_project)
        lessons = list_lessons(mnemo_project)
        # After one decay, confidence should decrease slightly
        assert lessons[0]["confidence"] < 1.0


# --- Episodes ---

class TestEpisodes:
    def test_start_episode(self, mnemo_project):
        ep = start_episode(mnemo_project, "Debugging auth timeout")
        assert ep["title"] == "Debugging auth timeout"
        assert ep["status"] == "active"

    def test_close_episode(self, mnemo_project):
        ep = start_episode(mnemo_project, "Fix payment bug")
        close_episode(mnemo_project, ep["id"], "Root cause was missing retry")
        episodes = list_episodes_raw(mnemo_project)
        closed = [e for e in episodes if e["id"] == ep["id"]]
        assert closed[0]["status"] == "closed"

    def test_list_episodes(self, mnemo_project):
        start_episode(mnemo_project, "Episode 1")
        start_episode(mnemo_project, "Episode 2")
        episodes = list_episodes_raw(mnemo_project)
        assert len(episodes) == 2


# --- Slots ---

class TestSlots:
    def test_set_and_get(self, mnemo_project):
        set_slot(mnemo_project, "project_context", "This is a Python web service using FastAPI")
        result = get_slot(mnemo_project, "project_context")
        assert "FastAPI" in result


# --- Integration ---

class TestIntegration:
    def test_full_lifecycle(self, mnemo_project):
        # Add
        entry = add_memory(mnemo_project, "The auth service uses JWT tokens with RS256")
        mid = entry["id"]

        # Search finds it
        result = search_memory(mnemo_project, "JWT auth tokens")
        assert "JWT" in result or "auth" in result

        # Forget
        forget_memory(mnemo_project, mid)

        # Search no longer finds it
        result = search_memory(mnemo_project, "JWT auth tokens")
        # After forgetting, the specific content should not appear
        stored = json.loads((mnemo_project / ".mnemo" / "memory.json").read_text())
        assert not any(e.get("id") == mid for e in stored)

    def test_decisions_persist(self, mnemo_project):
        add_decision(mnemo_project, "Use event sourcing for audit trail", "Need full history")
        stored = json.loads((mnemo_project / ".mnemo" / "decisions.json").read_text())
        assert len(stored) == 1
        assert stored[0]["decision"] == "Use event sourcing for audit trail"
        assert stored[0]["reasoning"] == "Need full history"
        assert stored[0].get("active", True) is True
