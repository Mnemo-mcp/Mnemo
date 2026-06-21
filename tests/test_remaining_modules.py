"""Sandbox tests for remaining untested modules: api_discovery, team_graph, velocity, regressions, onboarding."""

import json
import subprocess
from pathlib import Path

import pytest


# === API DISCOVERY ===

class TestApiDiscovery:
    """Tests for mnemo/api_discovery/."""

    def _make_repo(self, tmp_path: Path) -> Path:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".mnemo").mkdir()
        return repo

    def test_no_apis_found(self, tmp_path):
        from mnemo.api_discovery import discover_apis
        repo = self._make_repo(tmp_path)
        result = discover_apis(repo)
        assert "No APIs" in result

    def test_finds_openapi_spec(self, tmp_path):
        from mnemo.api_discovery import _find_openapi_specs
        repo = self._make_repo(tmp_path)
        spec = repo / "swagger.json"
        spec.write_text('{"openapi": "3.0.0"}')
        specs = _find_openapi_specs(repo)
        assert len(specs) == 1

    def test_parse_openapi_json(self, tmp_path):
        from mnemo.api_discovery import _parse_openapi
        spec = tmp_path / "openapi.json"
        spec.write_text(json.dumps({
            "info": {"title": "Auth API", "version": "1.0"},
            "paths": {
                "/login": {"post": {"summary": "Login user"}},
                "/users": {"get": {"summary": "List users"}},
            }
        }))
        result = _parse_openapi(spec)
        assert result["title"] == "Auth API"
        assert len(result["endpoints"]) == 2
        assert result["endpoints"][0]["method"] == "POST"

    def test_ignores_node_modules(self, tmp_path):
        from mnemo.api_discovery import _find_openapi_specs
        repo = self._make_repo(tmp_path)
        nm = repo / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "swagger.json").write_text("{}")
        specs = _find_openapi_specs(repo)
        assert len(specs) == 0

    def test_search_api_no_results(self, tmp_path):
        from mnemo.api_discovery import search_api
        repo = self._make_repo(tmp_path)
        result = search_api(repo, "auth")
        assert "No APIs" in result

    def test_search_api_with_spec(self, tmp_path):
        from mnemo.api_discovery import search_api
        repo = self._make_repo(tmp_path)
        (repo / "openapi.json").write_text(json.dumps({
            "info": {"title": "Test", "version": "1"},
            "paths": {"/auth/login": {"post": {"summary": "Authenticate"}}}
        }))
        result = search_api(repo, "auth")
        assert "auth" in result.lower()


# === TEAM GRAPH ===

class TestTeamGraph:
    """Tests for mnemo/team_graph/."""

    def test_no_git_repo(self, tmp_path):
        from mnemo.team_graph import build_team_graph
        result = build_team_graph(tmp_path)
        assert result == {}

    def test_get_experts_no_history(self, tmp_path):
        from mnemo.team_graph import get_experts
        result = get_experts(tmp_path, "auth")
        assert "No git history" in result

    def test_build_with_real_git(self, tmp_path):
        from mnemo.team_graph import build_team_graph
        repo = tmp_path / "r"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "dev@co.com"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Dev"], cwd=repo, capture_output=True)
        (repo / "src").mkdir()
        (repo / "src" / "main.py").write_text("# main")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo, capture_output=True)

        result = build_team_graph(repo)
        assert "expertise" in result
        assert "Dev" in result["expertise"]

    def test_who_last_touched(self, tmp_path):
        from mnemo.team_graph import who_last_touched
        repo = tmp_path / "r"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "a@b.com"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Alice"], cwd=repo, capture_output=True)
        (repo / "app.py").write_text("# app")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "add app"], cwd=repo, capture_output=True)

        result = who_last_touched(repo, "app.py")
        assert "Alice" in result


# === VELOCITY ===

class TestVelocity:
    """Tests for mnemo/velocity/."""

    def test_no_git_history(self, tmp_path):
        from mnemo.velocity import calculate_velocity
        result = calculate_velocity(tmp_path)
        assert "No git history" in result

    def test_with_commits(self, tmp_path):
        from mnemo.velocity import calculate_velocity
        repo = tmp_path / "r"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "d@e.com"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Dev"], cwd=repo, capture_output=True)
        (repo / "f.py").write_text("x = 1")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo, capture_output=True)

        result = calculate_velocity(repo)
        assert "Velocity" in result
        assert "Commits:" in result or "commits:" in result.lower()

    def test_git_log_returns_entries(self, tmp_path):
        from mnemo.velocity import _git_log
        repo = tmp_path / "r"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "d@e.com"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Dev"], cwd=repo, capture_output=True)
        (repo / "f.py").write_text("x = 1")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "test commit"], cwd=repo, capture_output=True)

        entries = _git_log(repo, days=30)
        assert len(entries) == 1
        assert entries[0]["author"] == "Dev"
        assert entries[0]["message"] == "test commit"


# === REGRESSIONS ===

class TestRegressions:
    """Tests for mnemo/quality/regressions.py."""

    def _make_repo(self, tmp_path: Path) -> Path:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".mnemo").mkdir()
        return repo

    def test_add_regression(self, tmp_path):
        from mnemo.quality.regressions import add_regression
        repo = self._make_repo(tmp_path)
        entry = add_regression(repo, "src/auth.py", "Token expires too fast", "Increased TTL to 15min", "test_token_expiry")
        assert entry["id"] == 1
        assert entry["file"] == "src/auth.py"
        assert entry["bug"] == "Token expires too fast"

    def test_check_regressions_none(self, tmp_path):
        from mnemo.quality.regressions import check_regressions
        repo = self._make_repo(tmp_path)
        result = check_regressions(repo, "src/auth.py")
        assert "No known regressions" in result

    def test_check_regressions_found(self, tmp_path):
        from mnemo.quality.regressions import add_regression, check_regressions
        repo = self._make_repo(tmp_path)
        add_regression(repo, "src/auth.py", "Token bug", "Fixed TTL")
        result = check_regressions(repo, "auth.py")
        assert "Token bug" in result
        assert "Fixed TTL" in result
        assert "regressed before" in result

    def test_list_regressions(self, tmp_path):
        from mnemo.quality.regressions import add_regression, list_regressions
        repo = self._make_repo(tmp_path)
        add_regression(repo, "a.py", "bug1", "fix1")
        add_regression(repo, "b.py", "bug2", "fix2")
        result = list_regressions(repo)
        assert "a.py" in result
        assert "b.py" in result
        assert "bug1" in result

    def test_list_empty(self, tmp_path):
        from mnemo.quality.regressions import list_regressions
        repo = self._make_repo(tmp_path)
        result = list_regressions(repo)
        assert "No regressions" in result


# === ONBOARDING ===

class TestOnboarding:
    """Tests for mnemo/onboarding/."""

    def _make_repo(self, tmp_path: Path) -> Path:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".mnemo").mkdir()
        return repo

    def test_generates_basic_guide(self, tmp_path):
        from mnemo.onboarding import generate_onboarding
        repo = self._make_repo(tmp_path)
        result = generate_onboarding(repo)
        assert "Onboarding Guide" in result
        assert "Getting Started" in result
        assert "mnemo init" in result

    def test_detects_knowledge_base(self, tmp_path):
        from mnemo.onboarding import generate_onboarding
        repo = self._make_repo(tmp_path)
        kb = repo / ".mnemo" / "knowledge"
        kb.mkdir()
        (kb / "runbooks.md").write_text("# Runbooks")
        result = generate_onboarding(repo)
        assert "Team Knowledge" in result
        assert "runbooks.md" in result

    def test_repo_name_in_output(self, tmp_path):
        from mnemo.onboarding import generate_onboarding
        repo = tmp_path / "my-service"
        repo.mkdir()
        (repo / ".mnemo").mkdir()
        result = generate_onboarding(repo)
        assert "my-service" in result
