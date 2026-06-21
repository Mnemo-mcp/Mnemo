"""Tests for graph-backed MCP tools — real Kuzu DB integration."""

import pytest
import real_ladybug as lbug

from mnemo.engine.schema import SCHEMA_STATEMENTS
from mnemo.tool_registry import get_handler


@pytest.fixture
def graph_project(tmp_path):
    """Create a tmp project with a real Kuzu graph populated with test data."""
    mnemo_dir = tmp_path / ".mnemo"
    mnemo_dir.mkdir()
    db_path = mnemo_dir / "graph.lbug"
    db = lbug.Database(str(db_path))
    conn = lbug.Connection(db)
    for stmt in SCHEMA_STATEMENTS:
        try:
            conn.execute(stmt)
        except RuntimeError:
            pass
    # Nodes
    conn.execute("CREATE (:File {path: 'src/auth.py', language: 'python', hash: 'abc', size: 500})")
    conn.execute("CREATE (:File {path: 'src/user.py', language: 'python', hash: 'def', size: 300})")
    conn.execute("CREATE (:Class {id: 'src/auth.py:AuthService', name: 'AuthService', file: 'src/auth.py', implements: '', docstring: 'Handles authentication'})")
    conn.execute("CREATE (:Class {id: 'src/user.py:UserService', name: 'UserService', file: 'src/user.py', implements: '', docstring: 'User management'})")
    conn.execute("CREATE (:Function {id: 'src/auth.py:login', name: 'login', file: 'src/auth.py', signature: 'def login(username, password)'})")
    conn.execute("CREATE (:Function {id: 'src/auth.py:logout', name: 'logout', file: 'src/auth.py', signature: 'def logout(token)'})")
    conn.execute("CREATE (:Function {id: 'src/user.py:get_user', name: 'get_user', file: 'src/user.py', signature: 'def get_user(user_id)'})")
    conn.execute("CREATE (:Method {id: 'src/auth.py:AuthService:authenticate', name: 'authenticate', class_name: 'AuthService', file: 'src/auth.py', signature: 'def authenticate(self, token)', visibility: 'public'})")
    # Relationships
    conn.execute("MATCH (a:Class {id: 'src/auth.py:AuthService'}), (m:Method {id: 'src/auth.py:AuthService:authenticate'}) CREATE (a)-[:HAS_METHOD]->(m)")
    conn.execute("MATCH (a:Function {id: 'src/auth.py:login'}), (b:Function {id: 'src/user.py:get_user'}) CREATE (a)-[:CALLS {confidence: 0.9, reason: 'import'}]->(b)")
    conn.execute("MATCH (a:File {path: 'src/auth.py'}), (b:File {path: 'src/user.py'}) CREATE (a)-[:IMPORTS]->(b)")
    # Supporting files
    (mnemo_dir / "memory.json").write_text("[]")
    (mnemo_dir / "decisions.json").write_text("[]")
    (mnemo_dir / "context.json").write_text("{}")
    return tmp_path


# --- tools/engine.py ---

class TestMnemoImpact:
    def test_finds_callers(self, graph_project):
        handler = get_handler("mnemo_impact")
        result = handler(graph_project, {"symbol": "get_user"})
        assert "login" in result

    def test_no_results(self, graph_project):
        handler = get_handler("mnemo_impact")
        result = handler(graph_project, {"symbol": "nonexistent"})
        assert "No upstream callers found" in result


class TestMnemoQuery:
    def test_raw_cypher(self, graph_project):
        handler = get_handler("mnemo_query")
        result = handler(graph_project, {"cypher": "MATCH (c:Class) RETURN c.name ORDER BY c.name"})
        assert "AuthService" in result
        assert "UserService" in result


class TestMnemoCommunities:
    def test_returns_valid_output(self, graph_project):
        handler = get_handler("mnemo_communities")
        result = handler(graph_project, {})
        # No communities inserted, but should still return valid output
        assert isinstance(result, str)


# --- tools/code.py ---

class TestMnemoLookup:
    def test_class(self, graph_project):
        handler = get_handler("mnemo_lookup")
        result = handler(graph_project, {"symbol": "AuthService"})
        assert "AuthService" in result
        assert "authenticate" in result
        assert "src/auth.py" in result

    def test_function(self, graph_project):
        handler = get_handler("mnemo_lookup")
        result = handler(graph_project, {"symbol": "login"})
        assert "login" in result
        assert "def login(username, password)" in result

    def test_not_found(self, graph_project):
        handler = get_handler("mnemo_lookup")
        result = handler(graph_project, {"symbol": "NonExistent"})
        assert "not found" in result.lower()


class TestMnemoMap:
    def test_produces_output(self, graph_project):
        handler = get_handler("mnemo_map")
        result = handler(graph_project, {})
        assert isinstance(result, str)
        assert len(result) > 0


# --- tools/graph.py ---

class TestMnemoGraph:
    def test_stats(self, graph_project):
        handler = get_handler("mnemo_graph")
        result = handler(graph_project, {"action": "stats"})
        assert "File: 2" in result
        assert "Class: 2" in result
        assert "Function: 3" in result

    def test_neighbors(self, graph_project):
        handler = get_handler("mnemo_graph")
        result = handler(graph_project, {"action": "neighbors", "node": "AuthService"})
        assert "authenticate" in result

    def test_find(self, graph_project):
        handler = get_handler("mnemo_graph")
        result = handler(graph_project, {"action": "find", "name": "Auth"})
        assert "AuthService" in result

    def test_find_by_type(self, graph_project):
        handler = get_handler("mnemo_graph")
        result = handler(graph_project, {"action": "find", "type": "Function", "name": "log"})
        assert "login" in result or "logout" in result


# --- tools/team.py ---

class TestImpactImports:
    def test_auth_imports_user_not_reverse(self, graph_project):
        handler = get_handler("mnemo_impact_imports")
        result = handler(graph_project, {"query": "auth.py"})
        # auth.py imports user.py, so user.py is NOT a dependent of auth.py
        # (nobody imports auth.py in our test data)
        assert "No dependents found" in result
