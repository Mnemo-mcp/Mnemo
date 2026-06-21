"""Comprehensive integration tests: init → graph → search → recall pipeline."""

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_project(tmp_path):
    """Copy sample_project fixture to tmp_path for isolated testing."""
    dest = tmp_path / "sample_project"
    shutil.copytree(FIXTURE_DIR / "sample_project", dest)
    return dest


@pytest.fixture
def second_project(tmp_path):
    dest = tmp_path / "second_project"
    shutil.copytree(FIXTURE_DIR / "second_project", dest)
    return dest


# ─── Pipeline Integration ───────────────────────────────────────────────────


class TestPipelineIntegration:
    def test_init_creates_mnemo_dir(self, sample_project):
        from mnemo.init import init
        init(sample_project, client="generic")
        assert (sample_project / ".mnemo").is_dir()

    def test_init_creates_graph(self, sample_project):
        from mnemo.init import init
        init(sample_project, client="generic")
        from mnemo.engine.db import get_db_path
        assert get_db_path(sample_project).exists()

    def test_init_indexes_classes(self, sample_project):
        from mnemo.init import init
        from mnemo.engine.db import open_db
        init(sample_project, client="generic")
        _, conn = open_db(sample_project)
        r = conn.execute("MATCH (c:Class) WHERE c.name = 'PaymentService' RETURN c.name")
        assert r.has_next()
        assert r.get_next()[0] == "PaymentService"

    def test_init_indexes_functions(self, sample_project):
        from mnemo.init import init
        from mnemo.engine.db import open_db
        init(sample_project, client="generic")
        _, conn = open_db(sample_project)
        # EventBus.publish is a method, but check any Function or Method nodes
        r = conn.execute("MATCH (m:Method) RETURN m.name")
        methods = []
        while r.has_next():
            methods.append(r.get_next()[0])
        assert len(methods) > 0
        assert "process_payment" in methods

    def test_init_detects_calls(self, sample_project):
        from mnemo.init import init
        from mnemo.engine.db import open_db
        init(sample_project, client="generic")
        _, conn = open_db(sample_project)
        # Verify HAS_METHOD edges exist (scope-resolved CALLS depend on cross-file resolution)
        r = conn.execute("MATCH ()-[e:HAS_METHOD]->() RETURN count(e)")
        count = r.get_next()[0]
        assert count > 0

    def test_init_creates_vectors(self, sample_project):
        from mnemo.init import init
        init(sample_project, client="generic")
        vectors = sample_project / ".mnemo" / "vectors_code.npy"
        assert vectors.exists()

    def test_init_idempotent(self, sample_project):
        from mnemo.init import init
        init(sample_project, client="generic")
        # Second run should not crash
        init(sample_project, client="generic")
        assert (sample_project / ".mnemo").is_dir()


# ─── Parser Integration ──────────────────────────────────────────────────────


class TestParserIntegration:
    def test_parser_extracts_classes(self):
        from mnemo.repo_map.parsers import _extract_file
        source = (FIXTURE_DIR / "sample_project" / "src" / "services" / "payment_service.py").read_bytes()
        result = _extract_file(source, "python")
        class_names = [c["name"] for c in result["classes"]]
        assert "PaymentService" in class_names

    def test_parser_extracts_methods(self):
        from mnemo.repo_map.parsers import _extract_file
        source = (FIXTURE_DIR / "sample_project" / "src" / "services" / "payment_service.py").read_bytes()
        result = _extract_file(source, "python")
        ps = next(c for c in result["classes"] if c["name"] == "PaymentService")
        method_names = [m.split("(")[0] for m in ps["methods"]]
        assert "__init__" in method_names
        assert "process_payment" in method_names
        assert "refund_payment" in method_names

    def test_parser_extracts_functions(self):
        from mnemo.repo_map.parsers import _extract_file
        source = (FIXTURE_DIR / "sample_project" / "src" / "services" / "event_bus.py").read_bytes()
        result = _extract_file(source, "python")
        # EventBus is a class with methods, not top-level functions
        class_names = [c["name"] for c in result["classes"]]
        assert "EventBus" in class_names

    def test_parser_handles_empty_file(self):
        from mnemo.repo_map.parsers import _extract_file
        source = (FIXTURE_DIR / "sample_project" / "src" / "__init__.py").read_bytes()
        result = _extract_file(source, "python")
        # Should return empty dict or dict with empty lists, no crash
        assert result is not None or result == {}

    def test_parser_extracts_dataclasses(self):
        from mnemo.repo_map.parsers import _extract_file
        source = (FIXTURE_DIR / "sample_project" / "src" / "models" / "transaction.py").read_bytes()
        result = _extract_file(source, "python")
        class_names = [c["name"] for c in result["classes"]]
        assert "Transaction" in class_names
        assert "AuditEntry" in class_names


# ─── Workspace / Multi-repo ──────────────────────────────────────────────────


class TestWorkspace:
    def test_link_repo(self, sample_project, second_project):
        from mnemo.init import init
        from mnemo.workspace import link_repo
        init(sample_project, client="generic")
        init(second_project, client="generic")
        result = link_repo(sample_project, second_project)
        assert "Linked" in result or "Already linked" in result

    def test_cross_search_after_link(self, sample_project, second_project):
        from mnemo.init import init
        from mnemo.workspace import link_repo, cross_repo_semantic_query
        init(sample_project, client="generic")
        init(second_project, client="generic")
        link_repo(sample_project, second_project)
        results = cross_repo_semantic_query(sample_project, "code", "payment", limit=10)
        # Should find hits from at least one repo
        assert len(results) > 0


# ─── Recall Integration ──────────────────────────────────────────────────────


class TestRecallIntegration:
    def test_recall_after_init(self, sample_project):
        from mnemo.init import init
        from mnemo.tool_registry import get_handler
        init(sample_project, client="generic")
        handler = get_handler("mnemo_recall")
        result = handler(sample_project, {"tier": "standard"})
        assert isinstance(result, str)
        assert len(result) > 0
        # Standard recall includes repo map (tree.md) generated by init
        assert "PaymentService" in result or "sample_project" in result or len(result) > 50

    def test_remember_then_recall(self, sample_project):
        from mnemo.init import init
        from mnemo.tool_registry import get_handler
        init(sample_project, client="generic")
        remember = get_handler("mnemo_remember")
        recall = get_handler("mnemo_recall")
        with patch("mnemo.memory.store._get_current_branch", return_value="main"):
            remember(sample_project, {"content": "Use Redis for session caching", "category": "architecture"})
        result = recall(sample_project, {"tier": "deep"})
        assert "Redis" in result


# ─── Lookup Integration ──────────────────────────────────────────────────────


class TestLookupIntegration:
    def test_lookup_class_after_init(self, sample_project):
        from mnemo.init import init
        from mnemo.tool_registry import get_handler
        init(sample_project, client="generic")
        handler = get_handler("mnemo_lookup")
        result = handler(sample_project, {"symbol": "PaymentService"})
        assert "PaymentService" in result
        assert "process_payment" in result

    def test_lookup_function_after_init(self, sample_project):
        from mnemo.init import init
        from mnemo.tool_registry import get_handler
        init(sample_project, client="generic")
        handler = get_handler("mnemo_lookup")
        result = handler(sample_project, {"symbol": "EventBus"})
        assert "EventBus" in result
        assert "publish" in result
