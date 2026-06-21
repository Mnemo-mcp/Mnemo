"""Sandbox tests for mnemo/knowledge/ — markdown knowledge base."""

from pathlib import Path
import pytest

from mnemo.knowledge import init_knowledge, search_knowledge, list_knowledge, _knowledge_path


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".mnemo").mkdir()
    return repo


class TestInitKnowledge:
    def test_creates_directory_and_readme(self, tmp_path):
        repo = _make_repo(tmp_path)
        kdir = init_knowledge(repo)
        assert kdir.exists()
        assert (kdir / "README.md").exists()
        content = (kdir / "README.md").read_text()
        assert "Knowledge Base" in content

    def test_idempotent(self, tmp_path):
        repo = _make_repo(tmp_path)
        init_knowledge(repo)
        init_knowledge(repo)  # Second call shouldn't overwrite
        assert (repo / ".mnemo" / "knowledge" / "README.md").exists()


class TestSearchKnowledge:
    def test_no_knowledge_dir(self, tmp_path):
        repo = _make_repo(tmp_path)
        result = search_knowledge(repo, "auth")
        assert "No knowledge base" in result

    def test_finds_matching_content(self, tmp_path):
        repo = _make_repo(tmp_path)
        kdir = _knowledge_path(repo)
        kdir.mkdir(parents=True)
        (kdir / "auth.md").write_text("# Authentication\n\nWe use JWT tokens with RS256.\nTokens expire after 15 minutes.\n")

        result = search_knowledge(repo, "JWT tokens")
        assert "JWT" in result
        assert "auth.md" in result

    def test_no_results(self, tmp_path):
        repo = _make_repo(tmp_path)
        kdir = _knowledge_path(repo)
        kdir.mkdir(parents=True)
        (kdir / "deploy.md").write_text("# Deployment\n\nDeploy to ECS Fargate.\n")

        result = search_knowledge(repo, "authentication")
        assert "No results" in result
        assert "deploy.md" in result  # Shows available files

    def test_multiple_files(self, tmp_path):
        repo = _make_repo(tmp_path)
        kdir = _knowledge_path(repo)
        kdir.mkdir(parents=True)
        (kdir / "auth.md").write_text("# Auth\n\nUse Redis for session tokens.\n")
        (kdir / "cache.md").write_text("# Caching\n\nRedis cluster at port 6379.\n")

        result = search_knowledge(repo, "Redis")
        assert "auth.md" in result or "cache.md" in result

    def test_subdirectories(self, tmp_path):
        repo = _make_repo(tmp_path)
        kdir = _knowledge_path(repo)
        subdir = kdir / "runbooks"
        subdir.mkdir(parents=True)
        (subdir / "deploy.md").write_text("# Deploy Runbook\n\nRun terraform apply.\n")

        result = search_knowledge(repo, "terraform")
        assert "deploy.md" in result


class TestListKnowledge:
    def test_no_knowledge_dir(self, tmp_path):
        repo = _make_repo(tmp_path)
        result = list_knowledge(repo)
        assert "No knowledge base" in result

    def test_lists_files_with_headings(self, tmp_path):
        repo = _make_repo(tmp_path)
        kdir = _knowledge_path(repo)
        kdir.mkdir(parents=True)
        (kdir / "arch.md").write_text("# Architecture Overview\n\nMicroservices.\n")
        (kdir / "api.md").write_text("# API Guide\n\nREST endpoints.\n")

        result = list_knowledge(repo)
        assert "arch.md" in result
        assert "Architecture Overview" in result
        assert "api.md" in result
        assert "API Guide" in result

    def test_empty_knowledge_dir(self, tmp_path):
        repo = _make_repo(tmp_path)
        kdir = _knowledge_path(repo)
        kdir.mkdir(parents=True)
        result = list_knowledge(repo)
        assert "Knowledge Base" in result
