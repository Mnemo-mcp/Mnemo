"""Tests for mnemo/enrichment.py — context enrichment pipeline."""

import json
from pathlib import Path
import pytest
from mnemo.enrichment import enrich_response


@pytest.fixture
def repo(tmp_path):
    """Create a repo with memories and decisions for enrichment testing."""
    mnemo_dir = tmp_path / ".mnemo"
    mnemo_dir.mkdir()
    (mnemo_dir / "memory.json").write_text(json.dumps([
        {"id": 1, "content": "Always use dependency injection in services", "category": "pattern", "timestamp": 1.0},
        {"id": 2, "content": "Fixed the auth bug in login handler", "category": "bug", "timestamp": 2.0},
    ]))
    (mnemo_dir / "decisions.json").write_text(json.dumps([
        {"id": 1, "decision": "Use PostgreSQL for persistence", "reasoning": "Better for our scale", "timestamp": 1.0, "active": True},
    ]))
    (mnemo_dir / "corrections.json").write_text(json.dumps([
        {"id": 1, "bad_pattern": "Using raw SQL", "correction": "Use parameterized queries", "timestamp": 1.0},
    ]))
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')
    return tmp_path


class TestEnrichContext:
    def test_returns_string(self, repo):
        result = enrich_response(repo, "mnemo_remember", "stored", {"content": "test"})
        assert isinstance(result, str)

    def test_no_crash_on_missing_mnemo(self, tmp_path):
        result = enrich_response(tmp_path, "mnemo_remember", "ok", {})
        assert isinstance(result, str)

    def test_no_crash_on_empty_args(self, repo):
        result = enrich_response(repo, "unknown_tool", "result", {})
        assert isinstance(result, str)
