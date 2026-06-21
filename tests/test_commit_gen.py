"""Sandbox tests for mnemo/commit_gen/ — commit message generation and mining."""

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from mnemo.commit_gen import (
    _classify_change,
    _extract_scope,
    _recent_memory,
    generate_commit_message,
)
from mnemo.commit_gen.mining import (
    _DECISION_SIGNALS,
    mine_commits_for_decisions,
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
    return repo


class TestClassifyChange:
    """Test conventional commit type classification."""

    def test_fix_from_diff(self):
        assert _classify_change("- broken\n+ fix the bug", "") == "fix"

    def test_feat_from_diff(self):
        assert _classify_change("+ add new feature", "") == "feat"

    def test_refactor_from_diff(self):
        assert _classify_change("refactor the handler", "") == "refactor"

    def test_test_from_stat(self):
        stat = " tests/test_auth.py | 50 ++++\n tests/test_user.py | 30 +++"
        assert _classify_change("", stat) == "test"

    def test_docs_from_stat(self):
        stat = " README.md | 10 ++++\n docs/setup.md | 5 ++"
        assert _classify_change("", stat) == "docs"

    def test_ci_from_stat(self):
        stat = " .github/workflows/ci.yml | 20 ++++"
        assert _classify_change("", stat) == "ci"

    def test_default_is_feat(self):
        assert _classify_change("some random change", "file.py | 3 +") == "feat"


class TestExtractScope:
    """Test scope extraction from file stat."""

    def test_single_file_scope(self):
        stat = " src/auth/handler.py | 10 +++"
        scope = _extract_scope(stat)
        assert scope in ("auth", "src")

    def test_common_directory(self):
        stat = " src/auth/login.py | 5 ++\n src/auth/token.py | 3 +"
        scope = _extract_scope(stat)
        assert scope == "auth"

    def test_no_directory(self):
        stat = " file.py | 3 +"
        scope = _extract_scope(stat)
        assert scope == ""

    def test_empty_stat(self):
        assert _extract_scope("") == ""

    def test_mixed_paths(self):
        stat = " src/a/foo.py | 1 +\n src/b/bar.py | 1 +"
        scope = _extract_scope(stat)
        assert scope == "src"


class TestRecentMemory:
    """Test loading recent memory entries."""

    def test_returns_empty_when_no_memory(self, tmp_path):
        repo = _make_repo(tmp_path)
        result = _recent_memory(repo)
        assert result == []

    def test_returns_recent_entries(self, tmp_path):
        import json
        repo = _make_repo(tmp_path)
        memories = [
            {"id": 1, "content": "Use PostgreSQL"},
            {"id": 2, "content": "Redis for caching"},
        ]
        (repo / ".mnemo" / "memory.json").write_text(json.dumps(memories))
        result = _recent_memory(repo, limit=5)
        assert "Use PostgreSQL" in result
        assert "Redis for caching" in result

    def test_respects_limit(self, tmp_path):
        import json
        repo = _make_repo(tmp_path)
        memories = [{"id": i, "content": f"memory {i}"} for i in range(10)]
        (repo / ".mnemo" / "memory.json").write_text(json.dumps(memories))
        result = _recent_memory(repo, limit=3)
        assert len(result) == 3


class TestGenerateCommitMessage:
    """Test full commit message generation."""

    def test_no_changes(self, tmp_path):
        repo = _make_repo(tmp_path)
        with patch("mnemo.commit_gen._git_diff_staged", return_value=""), \
             patch("mnemo.commit_gen._git_diff_stat", return_value=""):
            result = generate_commit_message(repo)
        assert "No changes" in result

    def test_single_file_change(self, tmp_path):
        repo = _make_repo(tmp_path)
        diff = "+def new_handler():\n+    pass"
        stat = " src/handlers.py | 3 +++"
        with patch("mnemo.commit_gen._git_diff_staged", return_value=diff), \
             patch("mnemo.commit_gen._git_diff_stat", return_value=stat):
            result = generate_commit_message(repo)
        # Should have a conventional commit format
        assert ":" in result
        assert "new_handler" in result or "handlers.py" in result

    def test_multiple_file_change(self, tmp_path):
        repo = _make_repo(tmp_path)
        diff = "some changes"
        stat = " src/a.py | 3 +++\n src/b.py | 2 ++"
        with patch("mnemo.commit_gen._git_diff_staged", return_value=diff), \
             patch("mnemo.commit_gen._git_diff_stat", return_value=stat):
            result = generate_commit_message(repo)
        assert "2 files" in result

    def test_test_files_classified_as_test(self, tmp_path):
        repo = _make_repo(tmp_path)
        diff = "+def test_something():\n+    assert True"
        stat = " tests/test_auth.py | 10 +++"
        with patch("mnemo.commit_gen._git_diff_staged", return_value=diff), \
             patch("mnemo.commit_gen._git_diff_stat", return_value=stat):
            result = generate_commit_message(repo)
        assert result.startswith("test")

    def test_bug_fix_classified(self, tmp_path):
        repo = _make_repo(tmp_path)
        diff = "-    return None  # bug here\n+    return result  # fixed"
        stat = " src/handler.py | 2 +-"
        with patch("mnemo.commit_gen._git_diff_staged", return_value=diff), \
             patch("mnemo.commit_gen._git_diff_stat", return_value=stat):
            result = generate_commit_message(repo)
        assert result.startswith("fix")


class TestDecisionSignals:
    """Test the regex that identifies decision-like commit messages."""

    def test_migration_detected(self):
        assert _DECISION_SIGNALS.search("Migrate from MySQL to PostgreSQL")

    def test_refactor_detected(self):
        assert _DECISION_SIGNALS.search("Refactor auth to use JWT")

    def test_replace_detected(self):
        assert _DECISION_SIGNALS.search("Replace Redis with Memcached")

    def test_normal_commit_not_detected(self):
        assert not _DECISION_SIGNALS.search("Add login button")

    def test_typo_fix_not_detected(self):
        assert not _DECISION_SIGNALS.search("Fix typo in README")


class TestMineCommits:
    """Test mining git history for decisions."""

    def test_returns_empty_without_git(self, tmp_path):
        """No git repo → empty result."""
        result = mine_commits_for_decisions(tmp_path)
        assert result == []

    def test_mines_decision_commits(self, tmp_path):
        """With mock git repo, finds decision-like commits."""
        # Create a real git repo with decision-like commits
        repo = tmp_path / "gitrepo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)

        # Create commits
        (repo / "file.py").write_text("# initial")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, capture_output=True)

        (repo / "file.py").write_text("# migrated")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Migrate database from MySQL to PostgreSQL"], cwd=repo, capture_output=True)

        (repo / "file.py").write_text("# refactored")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Refactor auth service to use token rotation"], cwd=repo, capture_output=True)

        result = mine_commits_for_decisions(repo)
        assert len(result) >= 2
        assert any("Migrate" in d["message"] for d in result)
        assert any("Refactor" in d["message"] for d in result)

    def test_skips_wip_commits(self, tmp_path):
        """WIP and trivial commits are skipped."""
        repo = tmp_path / "gitrepo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)

        (repo / "f.py").write_text("a")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "wip stuff"], cwd=repo, capture_output=True)

        (repo / "f.py").write_text("b")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "fix typo in docs"], cwd=repo, capture_output=True)

        result = mine_commits_for_decisions(repo)
        assert len(result) == 0
