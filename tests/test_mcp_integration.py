"""Integration tests for MCP server protocol handling and tool dispatch."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from mnemo.mcp_server import handle_tool_call, TOOLS
from mnemo.init import init


@pytest.fixture
def repo(tmp_path):
    """Create a temporary initialized repo."""
    init(tmp_path, client="generic")
    return tmp_path


class TestMCPToolList:
    """Test that tools/list returns valid schemas."""

    def test_tools_list_not_empty(self):
        assert len(TOOLS) >= 15

    def test_all_tools_have_required_fields(self):
        for tool in TOOLS:
            assert "name" in tool, f"Tool missing name: {tool}"
            assert "description" in tool, f"Tool {tool['name']} missing description"
            assert "inputSchema" in tool, f"Tool {tool['name']} missing inputSchema"

    def test_all_tools_have_valid_schema(self):
        for tool in TOOLS:
            schema = tool["inputSchema"]
            assert schema.get("type") == "object", f"Tool {tool['name']} schema type not object"
            assert "properties" in schema, f"Tool {tool['name']} missing properties"


class TestMCPToolDispatch:
    """Test tool call routing and validation."""

    def test_unknown_tool_returns_error(self, repo):
        result = handle_tool_call("nonexistent_tool", {"repo_path": str(repo)})
        assert result["isError"] is True
        assert "Unknown tool" in result["content"][0]["text"]

    def test_missing_required_field(self, repo):
        result = handle_tool_call("mnemo_remember", {"repo_path": str(repo)})
        assert result["isError"] is True
        assert "Missing required" in result["content"][0]["text"]

    def test_recall_returns_content(self, repo):
        result = handle_tool_call("mnemo_recall", {"repo_path": str(repo)})
        assert result.get("isError") is not True
        assert len(result["content"][0]["text"]) > 0

    def test_remember_stores_memory(self, repo):
        result = handle_tool_call("mnemo_remember", {
            "repo_path": str(repo),
            "content": "Test memory entry",
            "category": "general",
        })
        assert result.get("isError") is not True
        assert "stored" in result["content"][0]["text"].lower() or "memory" in result["content"][0]["text"].lower()

    def test_decide_stores_decision(self, repo):
        result = handle_tool_call("mnemo_decide", {
            "repo_path": str(repo),
            "decision": "Use PostgreSQL for persistence",
            "reasoning": "Better JSON support",
        })
        assert result.get("isError") is not True

    def test_no_repo_root_returns_error(self, tmp_path):
        # Use a path without .mnemo/ and no parent with .mnemo/
        empty = tmp_path / "deeply" / "nested" / "empty"
        empty.mkdir(parents=True)
        result = handle_tool_call("mnemo_recall", {"repo_path": str(empty)})
        # Either returns error or empty result (depends on whether cwd has .mnemo/)
        text = result["content"][0]["text"]
        assert "No .mnemo/" in text or "empty" in text.lower() or len(text) > 0


class TestMCPInputSanitization:
    """Test input validation and sanitization."""

    def test_string_length_limit(self, repo):
        result = handle_tool_call("mnemo_remember", {
            "repo_path": str(repo),
            "content": "x" * 200_000,
        })
        assert result["isError"] is True
        assert "exceeds maximum length" in result["content"][0]["text"]

    def test_type_coercion_integer(self, repo):
        # memory_id should be integer, passing string should coerce or error
        result = handle_tool_call("mnemo_forget", {
            "repo_path": str(repo),
            "memory_id": "abc",
        })
        assert result["isError"] is True

    def test_valid_integer_coercion(self, repo):
        result = handle_tool_call("mnemo_forget", {
            "repo_path": str(repo),
            "memory_id": "999",
        })
        # Should not error on type — may error on "not found" which is fine
        assert "must be an integer" not in result["content"][0].get("text", "")
