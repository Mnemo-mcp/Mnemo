"""Sandbox tests for mnemo/pr_gen/ — PR description generation."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from mnemo.pr_gen import (
    _active_task,
    _current_branch,
    _git_main_branch,
    _recent_memory,
    generate_pr_description,
)


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    mnemo = repo / ".mnemo"
    mnemo.mkdir()
    (mnemo / "memory.json").write_text("[]")
    (mnemo / "decisions.json").write_text("[]")
    (mnemo / "context.json").write_text("{}")
    (mnemo / "hashes.json").write_text("{}")
    (mnemo / "tasks.json").write_text("[]")
    (mnemo / "plans.json").write_text("[]")
    return repo


def _init_git(repo: Path) -> None:
    """Initialize a real git repo with an initial commit."""
    subprocess.run(["git", "init"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@t.com"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo, capture_output=True)
    (repo / "init.py").write_text("# init")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, capture_output=True)


class TestGitMainBranch:
    def test_detects_main(self, tmp_path):
        repo = tmp_path / "r"
        repo.mkdir()
        _init_git(repo)
        # Default branch is likely 'main' or 'master'
        result = _git_main_branch(repo)
        assert result in ("main", "master")

    def test_fallback_to_main(self, tmp_path):
        # Non-git dir falls back
        result = _git_main_branch(tmp_path)
        assert result == "main"


class TestCurrentBranch:
    def test_returns_branch_name(self, tmp_path):
        repo = tmp_path / "r"
        repo.mkdir()
        _init_git(repo)
        subprocess.run(["git", "checkout", "-b", "feature/auth"], cwd=repo, capture_output=True)
        assert _current_branch(repo) == "feature/auth"

    def test_returns_empty_for_non_git(self, tmp_path):
        assert _current_branch(tmp_path) == ""


class TestActiveTask:
    def test_returns_none_when_no_tasks(self, tmp_path):
        repo = _make_repo(tmp_path)
        assert _active_task(repo) is None

    def test_returns_active_task(self, tmp_path):
        repo = _make_repo(tmp_path)
        tasks = [
            {"task_id": "T-1", "description": "Add auth", "status": "done"},
            {"task_id": "T-2", "description": "Add caching", "status": "active"},
        ]
        (repo / ".mnemo" / "tasks.json").write_text(json.dumps(tasks))
        result = _active_task(repo)
        assert result["task_id"] == "T-2"


class TestRecentMemory:
    def test_empty(self, tmp_path):
        repo = _make_repo(tmp_path)
        assert _recent_memory(repo) == []

    def test_returns_content(self, tmp_path):
        repo = _make_repo(tmp_path)
        memories = [{"id": 1, "content": "Use Redis"}, {"id": 2, "content": "Deploy to ECS"}]
        (repo / ".mnemo" / "memory.json").write_text(json.dumps(memories))
        result = _recent_memory(repo)
        assert "Use Redis" in result


class TestGeneratePRDescription:
    def test_no_changes(self, tmp_path):
        repo = _make_repo(tmp_path)
        with patch("mnemo.pr_gen._git_branch_diff", return_value=("", "", "")), \
             patch("mnemo.pr_gen._current_branch", return_value="main"):
            result = generate_pr_description(repo)
        assert "No changes" in result

    def test_basic_pr_with_stat(self, tmp_path):
        repo = _make_repo(tmp_path)
        stat = " src/auth.py | 20 ++++\n src/models.py | 5 ++"
        diff = "+def authenticate(user, password):\n+    return True"
        commits = "abc1234 Add authentication endpoint\ndef5678 Add user model"

        with patch("mnemo.pr_gen._git_branch_diff", return_value=(stat, diff, commits)), \
             patch("mnemo.pr_gen._current_branch", return_value="feature/auth"):
            result = generate_pr_description(repo)

        assert "auth" in result.lower()
        assert "Changes" in result
        assert "Files" in result
        assert "Testing" in result
        assert "src/auth.py" in result

    def test_pr_with_active_task(self, tmp_path):
        repo = _make_repo(tmp_path)
        tasks = [{"task_id": "PROJ-42", "description": "Implement JWT auth", "status": "active", "notes": "Use RS256"}]
        (repo / ".mnemo" / "tasks.json").write_text(json.dumps(tasks))

        stat = " src/auth.py | 10 +"
        with patch("mnemo.pr_gen._git_branch_diff", return_value=(stat, "diff", "abc Fix")), \
             patch("mnemo.pr_gen._current_branch", return_value="feat/jwt"):
            result = generate_pr_description(repo)

        assert "PROJ-42" in result
        assert "JWT auth" in result
        assert "RS256" in result

    def test_pr_includes_memory_context(self, tmp_path):
        repo = _make_repo(tmp_path)
        memories = [{"id": 1, "content": "Authentication uses JWT with RS256 signing"}]
        (repo / ".mnemo" / "memory.json").write_text(json.dumps(memories))

        stat = " src/auth.py | 10 +"
        diff = "authentication JWT token validation handler"
        with patch("mnemo.pr_gen._git_branch_diff", return_value=(stat, diff, "abc Add auth")), \
             patch("mnemo.pr_gen._current_branch", return_value="feat/auth"):
            result = generate_pr_description(repo)

        assert "Context" in result
        assert "JWT" in result

    def test_real_git_repo(self, tmp_path):
        """Integration test with actual git operations."""
        repo = _make_repo(tmp_path)
        _init_git(repo)

        # Create feature branch with changes
        subprocess.run(["git", "checkout", "-b", "feature/test"], cwd=repo, capture_output=True)
        (repo / "feature.py").write_text("def new_feature():\n    return True\n")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add new feature"], cwd=repo, capture_output=True)

        result = generate_pr_description(repo)
        # Should have some content (not "no changes")
        assert "No changes" not in result
        assert "feature" in result.lower() or "Changes" in result
