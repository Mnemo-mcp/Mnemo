"""Tests for mnemo/engine/query.py — real Kuzu DB integration."""

import pytest
import real_ladybug as lbug

from mnemo.engine.query import execute, execute_one, execute_scalar, with_connection


@pytest.fixture
def db_conn(tmp_path):
    """Create a real Kuzu DB with a small test graph."""
    db_path = tmp_path / "test.lbug"
    db = lbug.Database(str(db_path))
    conn = lbug.Connection(db)
    conn.execute("CREATE NODE TABLE Person(name STRING, age INT64, PRIMARY KEY(name))")
    conn.execute("CREATE REL TABLE KNOWS(FROM Person TO Person)")
    conn.execute("CREATE (p:Person {name: 'Alice', age: 30})")
    conn.execute("CREATE (p:Person {name: 'Bob', age: 25})")
    conn.execute("CREATE (p:Person {name: 'Carol', age: 35})")
    conn.execute("MATCH (a:Person {name: 'Alice'}), (b:Person {name: 'Bob'}) CREATE (a)-[:KNOWS]->(b)")
    return conn


class TestExecute:
    def test_returns_list_of_rows(self, db_conn):
        rows = execute(db_conn, "MATCH (p:Person) RETURN p.name, p.age ORDER BY p.name")
        assert len(rows) == 3
        assert rows[0] == ["Alice", 30]
        assert rows[1] == ["Bob", 25]
        assert rows[2] == ["Carol", 35]

    def test_empty_result(self, db_conn):
        rows = execute(db_conn, "MATCH (p:Person {name: 'Nobody'}) RETURN p.name")
        assert rows == []

    def test_parameterized_query(self, db_conn):
        rows = execute(db_conn, "MATCH (p:Person) WHERE p.age > $min_age RETURN p.name ORDER BY p.name", {"min_age": 28})
        assert len(rows) == 2
        assert rows[0] == ["Alice"]
        assert rows[1] == ["Carol"]


class TestExecuteOne:
    def test_returns_first_row(self, db_conn):
        row = execute_one(db_conn, "MATCH (p:Person {name: 'Bob'}) RETURN p.name, p.age")
        assert row == ["Bob", 25]

    def test_returns_none_when_empty(self, db_conn):
        row = execute_one(db_conn, "MATCH (p:Person {name: 'Nobody'}) RETURN p.name")
        assert row is None

    def test_parameterized(self, db_conn):
        row = execute_one(db_conn, "MATCH (p:Person {name: $n}) RETURN p.age", {"n": "Carol"})
        assert row == [35]


class TestExecuteScalar:
    def test_returns_first_value(self, db_conn):
        val = execute_scalar(db_conn, "MATCH (p:Person {name: 'Alice'}) RETURN p.age")
        assert val == 30

    def test_returns_none_when_empty(self, db_conn):
        val = execute_scalar(db_conn, "MATCH (p:Person {name: 'Nobody'}) RETURN p.age")
        assert val is None

    def test_parameterized(self, db_conn):
        val = execute_scalar(db_conn, "MATCH (p:Person) WHERE p.name = $name RETURN p.age", {"name": "Bob"})
        assert val == 25


class TestWithConnection:
    def test_raises_file_not_found_when_no_db(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="No graph database"):
            with with_connection(tmp_path) as _conn:
                pass

    def test_opens_real_db(self, tmp_path):
        # Create a valid .mnemo/graph.lbug
        db_path = tmp_path / ".mnemo" / "graph.lbug"
        db_path.parent.mkdir(parents=True)
        db = lbug.Database(str(db_path))
        conn = lbug.Connection(db)
        conn.execute("CREATE NODE TABLE T(id STRING, PRIMARY KEY(id))")
        del conn, db

        with with_connection(tmp_path) as conn:
            result = execute(conn, "MATCH (t:T) RETURN t.id")
            assert result == []
