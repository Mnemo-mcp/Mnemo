"""Tests for engine/db.py and engine/clustering.py."""

from pathlib import Path
import pytest
from mnemo.engine.db import open_db, get_db_path, init_schema, reset_db
from mnemo.engine.clustering import detect_communities


@pytest.fixture
def db(tmp_path):
    (tmp_path / ".mnemo").mkdir()
    reset_db(tmp_path)
    _, conn = open_db(tmp_path)
    init_schema(conn)
    return tmp_path, conn


class TestDB:
    def test_get_db_path(self, tmp_path):
        path = get_db_path(tmp_path)
        assert ".mnemo" in str(path)
        assert "graph.lbug" in str(path)

    def test_open_creates_db(self, tmp_path):
        (tmp_path / ".mnemo").mkdir()
        _, conn = open_db(tmp_path)
        assert conn is not None

    def test_schema_creates_tables(self, db):
        _, conn = db
        # Should be able to query File table
        r = conn.execute("MATCH (f:File) RETURN count(f)")
        assert r.get_next()[0] == 0

    def test_insert_and_query(self, db):
        _, conn = db
        conn.execute("CREATE (f:File {path: 'test.py', language: 'python', hash: 'abc123', size: 100})")
        r = conn.execute("MATCH (f:File) RETURN f.path")
        assert r.get_next()[0] == "test.py"


class TestClustering:
    def test_no_communities_on_empty_graph(self, db):
        _, conn = db
        count = detect_communities(conn)
        assert count == 0

    def test_communities_detected(self, db):
        _, conn = db
        # Create some connected nodes
        for i in range(5):
            conn.execute(f"CREATE (f:Function {{id: 'a:{i}', name: 'func{i}', file: 'a.py', signature: ''}})")
        for i in range(5):
            conn.execute(f"CREATE (f:Function {{id: 'b:{i}', name: 'gunc{i}', file: 'b.py', signature: ''}})")
        # Connect within groups
        conn.execute("CREATE (f:File {path: 'a.py', language: 'python', hash: 'x', size: 1})")
        conn.execute("CREATE (f:File {path: 'b.py', language: 'python', hash: 'y', size: 1})")
        for i in range(5):
            conn.execute(f"MATCH (f:File {{path: 'a.py'}}), (fn:Function {{id: 'a:{i}'}}) CREATE (f)-[:FILE_DEFINES_FUNCTION]->(fn)")
            conn.execute(f"MATCH (f:File {{path: 'b.py'}}), (fn:Function {{id: 'b:{i}'}}) CREATE (f)-[:FILE_DEFINES_FUNCTION]->(fn)")
        count = detect_communities(conn)
        assert count >= 1
