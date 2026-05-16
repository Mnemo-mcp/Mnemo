"""MNO-031: Full cycle integration tests — remember → search → recall."""

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from mnemo.memory import add_memory, add_decision, search_memory
from mnemo.storage import Collections, get_storage


def make_repo(tmp_path):
    d = tmp_path / ".mnemo"
    d.mkdir()
    for f in ("memory.json", "decisions.json", "plans.json"):
        (d / f).write_text("[]")
    (d / "context.json").write_text("{}")
    (d / "hashes.json").write_text("{}")
    (d / "tasks.json").write_text("[]")
    return tmp_path


class TestRememberSearchRecallCycle:
    def test_store_and_search(self, tmp_path):
        repo = make_repo(tmp_path)
        contents = [
            "Use PostgreSQL for the user database",
            "Redis is the caching layer for sessions",
            "Deploy to AWS ECS with Fargate",
            "Authentication uses JWT tokens with RS256",
            "Frontend built with React and TypeScript",
        ]
        with patch("mnemo.memory._get_current_branch", return_value="main"):
            for c in contents:
                add_memory(repo, c, "architecture")

        result = search_memory(repo, "caching layer")
        assert "Redis" in result


class TestContradictionSupersedes:
    def test_supersedes_old_memory(self, tmp_path):
        repo = make_repo(tmp_path)
        with patch("mnemo.memory._get_current_branch", return_value="main"):
            add_memory(repo, "Use Redis for caching user sessions in the auth service layer", "architecture")
            add_memory(repo, "Use Memcached for caching user sessions in the auth service layer instead of Redis", "architecture")

        storage = get_storage(repo)
        entries = storage.read_collection(Collections.MEMORY)
        superseded = [e for e in entries if e.get("superseded_by")]
        assert len(superseded) >= 1
        assert "Redis" in superseded[0]["content"]


class TestDedupPreventsDuplicates:
    def test_same_content_deduped(self, tmp_path):
        repo = make_repo(tmp_path)
        with patch("mnemo.memory._get_current_branch", return_value="main"):
            add_memory(repo, "Always use parameterized queries for SQL", "preference")
            add_memory(repo, "Always use parameterized queries for SQL", "preference")

        storage = get_storage(repo)
        entries = storage.read_collection(Collections.MEMORY)
        assert len(entries) == 1


class TestDecisionContradiction:
    def test_conflicting_decisions(self, tmp_path):
        repo = make_repo(tmp_path)
        add_decision(repo, "Use MongoDB as the primary database for storing user profile data")
        add_decision(repo, "Use PostgreSQL as the primary database for storing user profile data instead of MongoDB")

        storage = get_storage(repo)
        decisions = storage.read_collection(Collections.DECISIONS)
        inactive = [d for d in decisions if not d.get("active", True)]
        assert len(inactive) >= 1
        assert "MongoDB" in inactive[0]["decision"]
