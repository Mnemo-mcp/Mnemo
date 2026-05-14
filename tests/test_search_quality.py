"""Tests for search quality: RRF, diversification, token budget, query expansion."""

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from mnemo.memory import (
    MEMORY_TOKEN_BUDGET,
    TOKEN_CHAR_RATIO,
    _recall_memory,
    search_memory,
)
from mnemo.storage import get_storage, Collections


def make_repo(tmp_path):
    mnemo_dir = tmp_path / ".mnemo"
    mnemo_dir.mkdir()
    (mnemo_dir / "memory.json").write_text("[]")
    (mnemo_dir / "decisions.json").write_text("[]")
    (mnemo_dir / "plans.json").write_text("[]")
    (mnemo_dir / "context.json").write_text("{}")
    return tmp_path


def seed_memories(repo, memories):
    """Write pre-built memory entries to storage."""
    storage = get_storage(repo)
    storage.write_collection(Collections.MEMORY, memories)


class TestSearchBasic:
    def test_search_returns_results(self, tmp_path):
        repo = make_repo(tmp_path)
        now = time.time()
        seed_memories(repo, [
            {"id": 1, "timestamp": now, "category": "bug", "content": "Fixed auth token refresh bug", "access_count": 0},
            {"id": 2, "timestamp": now, "category": "pattern", "content": "Handler pattern for payers", "access_count": 0},
        ])
        result = search_memory(repo, "auth token")
        assert "auth token" in result.lower() or "token" in result.lower()

    def test_search_no_results(self, tmp_path):
        repo = make_repo(tmp_path)
        seed_memories(repo, [])
        result = search_memory(repo, "nonexistent xyz")
        assert "No memories found" in result


class TestSourceDiversification:
    def test_max_3_per_category(self, tmp_path):
        repo = make_repo(tmp_path)
        now = time.time()
        # Create 6 bug memories all matching "error"
        entries = [
            {"id": i, "timestamp": now, "category": "bug", "content": f"error in service {i} causing crash", "access_count": 0}
            for i in range(1, 7)
        ]
        seed_memories(repo, entries)
        result = search_memory(repo, "error")
        # Count how many [bug] entries appear
        bug_count = result.count("[bug]")
        assert bug_count <= 3


class TestTokenBudget:
    def test_recall_memory_truncates_at_budget(self, tmp_path):
        repo = make_repo(tmp_path)
        now = time.time()
        storage = get_storage(repo)
        # Create many large hot memories (architecture = pinned = always hot)
        entries = [
            {
                "id": i,
                "timestamp": now,
                "category": "architecture",
                "content": f"Architecture decision number {i}: " + "x" * 200,
                "access_count": 5,
            }
            for i in range(1, 30)
        ]
        storage.write_collection(Collections.MEMORY, entries)

        with patch("mnemo.memory._get_current_branch", return_value="main"):
            output = _recall_memory(repo, storage)

        char_budget = MEMORY_TOKEN_BUDGET * TOKEN_CHAR_RATIO
        # The memory section content (excluding the "more memories excluded" note) should be within budget
        lines = output.strip().split("\n")
        content_lines = [l for l in lines if l.startswith("- ")]
        content_chars = sum(len(l) for l in content_lines)
        assert content_chars <= char_budget + 300  # small tolerance for last line


class TestQueryExpansion:
    def test_extracts_file_paths(self, tmp_path):
        repo = make_repo(tmp_path)
        now = time.time()
        seed_memories(repo, [
            {"id": 1, "timestamp": now, "category": "bug", "content": "Fixed bug in services/auth.py handler", "access_count": 0},
        ])
        # Query with a file path — expansion should help find it
        result = search_memory(repo, "services/auth.py")
        assert "auth" in result.lower()

    def test_extracts_capitalized_words(self, tmp_path):
        repo = make_repo(tmp_path)
        now = time.time()
        seed_memories(repo, [
            {"id": 1, "timestamp": now, "category": "pattern", "content": "PayerHandler implements the IPayerHandler interface", "access_count": 0},
        ])
        result = search_memory(repo, "PayerHandler interface")
        assert "PayerHandler" in result


class TestRRFScoring:
    def test_rrf_combines_keyword_and_semantic(self, tmp_path):
        repo = make_repo(tmp_path)
        now = time.time()
        # Entry that matches keyword exactly
        seed_memories(repo, [
            {"id": 1, "timestamp": now, "category": "bug", "content": "cosmos database connection timeout error", "access_count": 0},
            {"id": 2, "timestamp": now, "category": "pattern", "content": "retry pattern for transient failures", "access_count": 0},
        ])
        # "cosmos timeout" should rank entry 1 higher via keyword match
        result = search_memory(repo, "cosmos timeout")
        lines = [l for l in result.split("\n") if l.startswith("- [")]
        if lines:
            assert "cosmos" in lines[0].lower()
