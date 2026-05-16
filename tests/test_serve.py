"""Tests for mnemo/serve.py API endpoints."""

from pathlib import Path
import json
import pytest
from mnemo.engine.pipeline import run_pipeline
from mnemo.serve import MnemoAPIHandler


@pytest.fixture
def repo(tmp_path):
    (tmp_path / ".mnemo").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "api-test"\n')
    (tmp_path / "main.py").write_text('def handler(): pass\nclass Service: pass\n')
    run_pipeline(tmp_path, force=True)
    # Add a memory
    mem_file = tmp_path / ".mnemo" / "memory.json"
    mem_file.write_text(json.dumps([{"id": 1, "content": "test mem", "category": "general", "timestamp": 1}]))
    return tmp_path


@pytest.fixture
def handler(repo):
    MnemoAPIHandler.repo_root = repo
    h = MnemoAPIHandler.__new__(MnemoAPIHandler)
    h.repo_root = repo
    return h


class TestStatsEndpoint:
    def test_returns_counts(self, handler):
        result = handler._stats({})
        assert result["nodes"] > 0
        assert result["edges"] >= 0
        assert "files" in result
        assert "classes" in result
        assert "functions" in result


class TestGraphEndpoint:
    def test_returns_nodes_and_edges(self, handler):
        result = handler._graph({})
        assert "nodes" in result
        assert "edges" in result
        assert len(result["nodes"]) > 0

    def test_has_project_nodes(self, handler):
        result = handler._graph({})
        types = {n["type"] for n in result["nodes"]}
        assert "project" in types

    def test_has_file_nodes(self, handler):
        result = handler._graph({})
        types = {n["type"] for n in result["nodes"]}
        assert "file" in types


class TestSearchEndpoint:
    def test_empty_query(self, handler):
        result = handler._search({"q": [""]})
        assert result == {"results": []}

    def test_finds_class(self, handler):
        result = handler._search({"q": ["Service"]})
        assert any(r["name"] == "Service" for r in result["results"])


class TestMemoryEndpoint:
    def test_returns_memories(self, handler):
        result = handler._memory({})
        assert "memories" in result
        assert len(result["memories"]) == 1
        assert result["memories"][0]["content"] == "test mem"


class TestHealthEndpoint:
    def test_returns_status(self, handler):
        result = handler._health({})
        assert result["status"] in ("healthy", "degraded")
        assert result["checks"]["graph_db"] is True


class TestOverviewEndpoint:
    def test_combines_stats_and_memory(self, handler):
        result = handler._overview({})
        assert "nodes" in result
        assert "memory_count" in result
        assert result["memory_count"] == 1
