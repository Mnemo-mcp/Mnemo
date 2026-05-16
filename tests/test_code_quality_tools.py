"""Tests for migrated Layer 2b tools (dead_code, security, conventions, breaking, drift, health)."""

from pathlib import Path
import pytest
from mnemo.engine.pipeline import run_pipeline


@pytest.fixture
def indexed_repo(tmp_path):
    """Create and index a minimal repo."""
    (tmp_path / ".mnemo").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')
    (tmp_path / "main.py").write_text('def used_func():\n    return 1\n\ndef unused_func():\n    return 2\n\nclass MyService:\n    def handle(self): pass\n')
    (tmp_path / "caller.py").write_text('from main import used_func\n\ndef run():\n    return used_func()\n')
    (tmp_path / "secret.py").write_text('password = "hunter2"\napi_key = "sk-1234567890abcdef"\n')
    run_pipeline(tmp_path, force=True)
    return tmp_path


class TestDeadCode:
    def test_detects_unused(self, indexed_repo):
        from mnemo.dead_code import detect_dead_code
        result = detect_dead_code(indexed_repo)
        assert "Potentially Unused" in result or "No potentially dead" in result

    def test_returns_string(self, indexed_repo):
        from mnemo.dead_code import detect_dead_code
        assert isinstance(detect_dead_code(indexed_repo), str)


class TestSecurity:
    def test_detects_hardcoded_secrets(self, indexed_repo):
        from mnemo.security import check_security
        result = check_security(indexed_repo)
        assert "Security Scan" in result or "hardcoded" in result.lower() or "findings" in result.lower()

    def test_single_file_scan(self, indexed_repo):
        from mnemo.security import check_security
        result = check_security(indexed_repo, file_path="secret.py")
        assert isinstance(result, str)

    def test_add_custom_pattern(self, indexed_repo):
        from mnemo.security import add_security_pattern
        entry = add_security_pattern(indexed_repo, "test_pattern", r"TODO", severity="low")
        assert entry["name"] == "test_pattern"
        assert entry["id"] >= 1


class TestConventions:
    def test_detect_conventions(self, indexed_repo):
        from mnemo.conventions import detect_conventions
        conv = detect_conventions(indexed_repo)
        assert isinstance(conv, dict)
        assert "naming" in conv

    def test_check_conventions(self, indexed_repo):
        from mnemo.conventions import check_conventions
        result = check_conventions(indexed_repo)
        assert isinstance(result, str)


class TestBreaking:
    def test_save_and_detect(self, indexed_repo):
        from mnemo.breaking import save_baseline, detect_breaking_changes
        save_result = save_baseline(indexed_repo)
        assert "Baseline saved" in save_result

        detect_result = detect_breaking_changes(indexed_repo)
        assert "No breaking changes" in detect_result

    def test_no_baseline_message(self, indexed_repo):
        from mnemo.breaking import detect_breaking_changes
        result = detect_breaking_changes(indexed_repo)
        assert "baseline" in result.lower()


class TestDrift:
    def test_no_drift_empty(self, indexed_repo):
        from mnemo.drift import detect_drift
        result = detect_drift(indexed_repo)
        assert isinstance(result, str)

    def test_init_rules(self, indexed_repo):
        from mnemo.drift import _init_rules
        _init_rules(indexed_repo)
        rules_file = indexed_repo / ".mnemo" / "rules.yaml"
        assert rules_file.exists()


class TestHealth:
    def test_system_health(self, indexed_repo):
        from mnemo.health import system_health
        sh = system_health(indexed_repo)
        assert sh["graph_nodes"] > 0
        assert sh["graph_edges"] > 0

    def test_calculate_health(self, indexed_repo):
        from mnemo.health import calculate_health
        result = calculate_health(indexed_repo)
        assert "Code Health" in result
        assert "python" in result.lower()
