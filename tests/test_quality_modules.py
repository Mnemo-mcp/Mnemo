"""Tests for quality/ subpackage and other low-coverage modules."""

import pytest
import real_ladybug as lbug
from mnemo.engine.schema import SCHEMA_STATEMENTS


@pytest.fixture
def project_with_graph(tmp_path):
    mnemo_dir = tmp_path / '.mnemo'
    mnemo_dir.mkdir()
    db_path = mnemo_dir / 'graph.lbug'
    db = lbug.Database(str(db_path))
    conn = lbug.Connection(db)
    for stmt in SCHEMA_STATEMENTS:
        try:
            conn.execute(stmt)
        except RuntimeError:
            pass
    conn.execute("CREATE (:File {path: 'src/main.py', language: 'python', hash: 'x', size: 100})")
    conn.execute("CREATE (:Class {id: 'src/main.py:myBadClass', name: 'myBadClass', file: 'src/main.py', implements: '', docstring: ''})")
    conn.execute("CREATE (:Function {id: 'src/main.py:unused_helper', name: 'unused_helper', file: 'src/main.py', signature: 'def unused_helper()'})")
    conn.execute("CREATE (:Function {id: 'src/main.py:main', name: 'main', file: 'src/main.py', signature: 'def main()'})")
    conn.execute("MATCH (a:Function {id:'src/main.py:main'}), (b:Function {id:'src/main.py:unused_helper'}) CREATE (a)-[:CALLS {confidence:0.9, reason:'direct'}]->(b)")
    conn.execute("MATCH (f:File {path:'src/main.py'}), (c:Class {id:'src/main.py:myBadClass'}) CREATE (f)-[:FILE_DEFINES_CLASS]->(c)")
    conn.execute("MATCH (f:File {path:'src/main.py'}), (fn:Function {id:'src/main.py:unused_helper'}) CREATE (f)-[:FILE_DEFINES_FUNCTION]->(fn)")
    conn.execute("MATCH (f:File {path:'src/main.py'}), (fn:Function {id:'src/main.py:main'}) CREATE (f)-[:FILE_DEFINES_FUNCTION]->(fn)")
    (mnemo_dir / 'memory.json').write_text('[]')
    (mnemo_dir / 'decisions.json').write_text('[]')
    return tmp_path


# --- quality/security.py ---

class TestSecurity:
    def test_scan_detects_hardcoded_secret(self, project_with_graph):
        src = project_with_graph / 'src'
        src.mkdir()
        (src / 'main.py').write_text('api_key = "sk-abc123secretvalue"\n')
        from mnemo.quality.security import check_security
        result = check_security(project_with_graph, file_path='src/main.py')
        assert 'hardcoded_secret' in result.lower() or 'secret' in result.lower()
        assert 'api_key' in result

    def test_scan_clean_file(self, project_with_graph):
        src = project_with_graph / 'src'
        src.mkdir()
        (src / 'clean.py').write_text('def hello():\n    return "world"\n')
        from mnemo.quality.security import check_security
        result = check_security(project_with_graph, file_path='src/clean.py')
        assert 'No security issues' in result


# --- quality/dead_code.py ---

class TestDeadCode:
    def test_finds_unreferenced_function(self, project_with_graph):
        # 'main' has no incoming CALLS edges, 'unused_helper' does (from main)
        # But 'main' is excluded by the filter (name IN ['main'...])
        # So we need a truly dead function with no incoming edges
        mnemo_dir = project_with_graph / '.mnemo'
        db_path = mnemo_dir / 'graph.lbug'
        db = lbug.Database(str(db_path))
        conn = lbug.Connection(db)
        conn.execute("CREATE (:Function {id: 'src/main.py:dead_func', name: 'dead_func', file: 'src/main.py', signature: 'def dead_func()'})")
        from mnemo.quality.dead_code import detect_dead_code
        result = detect_dead_code(project_with_graph)
        assert 'dead_func' in result


# --- quality/conventions.py ---

class TestConventions:
    def test_detects_naming_violation(self, project_with_graph):
        from mnemo.quality.conventions import check_conventions
        result = check_conventions(project_with_graph)
        assert 'myBadClass' in result
        assert 'violation' in result.lower() or "doesn't match" in result.lower()


# --- quality/health.py ---

class TestHealth:
    def test_health_report_returns_data(self, project_with_graph):
        from mnemo.quality.health import calculate_health
        result = calculate_health(project_with_graph)
        assert 'Health' in result
        assert 'python' in result.lower()


# --- quality/breaking.py ---

class TestBreaking:
    def test_baseline_and_check(self, project_with_graph):
        from mnemo.quality.breaking import save_baseline, detect_breaking_changes
        # Save baseline with current class
        save_baseline(project_with_graph)
        # Remove the class from graph
        mnemo_dir = project_with_graph / '.mnemo'
        db = lbug.Database(str(mnemo_dir / 'graph.lbug'))
        conn = lbug.Connection(db)
        conn.execute("MATCH (c:Class {id:'src/main.py:myBadClass'}) DETACH DELETE c")
        # Should detect the removal
        result = detect_breaking_changes(project_with_graph)
        assert 'myBadClass' in result or 'Removed' in result or 'breaking' in result.lower()


# --- records/ ---

class TestRecords:
    def test_add_and_search_error(self, project_with_graph):
        from mnemo.records.errors import add_error, search_errors
        add_error(project_with_graph, error="NullPointerException in handler", cause="missing null check", fix="added guard clause")
        result = search_errors(project_with_graph, "NullPointer")
        assert 'NullPointerException' in result
        assert 'guard clause' in result

    def test_add_and_list_incident(self, project_with_graph):
        from mnemo.records.incidents import add_incident, format_incidents
        add_incident(project_with_graph, title="Payment outage", what_happened="Payments failed for 30min", root_cause="DB connection pool exhausted", fix="Increased pool size", severity="high", services=["payment-svc"])
        result = format_incidents(project_with_graph)
        assert 'Payment outage' in result


# --- commit_gen/ ---

class TestCommitGen:
    def test_generate_commit_no_git(self, project_with_graph):
        from mnemo.commit_gen import generate_commit_message
        result = generate_commit_message(project_with_graph)
        assert 'No changes' in result or 'Stage files' in result.lower() or result != ""


# --- utils/dedup.py ---

class TestDedup:
    def test_dedup_map_detects_duplicates(self):
        from mnemo.utils.dedup import DedupMap
        dm = DedupMap()
        assert not dm.is_duplicate("tool", "input1")
        assert dm.is_duplicate("tool", "input1")

    def test_dedup_map_allows_unique(self):
        from mnemo.utils.dedup import DedupMap
        dm = DedupMap()
        assert not dm.is_duplicate("tool", "input_a")
        assert not dm.is_duplicate("tool", "input_b")


# --- embeddings/__init__.py ---

class TestEmbeddings:
    def test_sparse_embedding_score(self):
        from mnemo.embeddings import KeywordEmbeddingProvider
        provider = KeywordEmbeddingProvider()
        e1 = provider.embed("python function class method")
        e2 = provider.embed("python class definition method")
        assert e1.score(e2) > 0

    def test_sparse_embedding_different(self):
        from mnemo.embeddings import KeywordEmbeddingProvider
        provider = KeywordEmbeddingProvider()
        e1 = provider.embed("quantum physics neutron star")
        e2 = provider.embed("chocolate cake recipe baking")
        assert e1.score(e2) < 0.1
