"""Tests for consolidated tool routing — verifies all internal tools are reachable
via the 15 exposed tools using natural language scenarios."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from mnemo.init import init
from mnemo.mcp_server import handle_tool_call


@pytest.fixture
def repo(tmp_path):
    """Create initialized repo with some test data."""
    init(tmp_path, client="generic")
    # Seed some memory
    handle_tool_call("mnemo_remember", {"repo_path": str(tmp_path), "content": "We use Redis for caching", "category": "architecture"})
    handle_tool_call("mnemo_remember", {"repo_path": str(tmp_path), "content": "Fixed NullRef in PaymentService by adding null check", "category": "bug"})
    handle_tool_call("mnemo_decide", {"repo_path": str(tmp_path), "decision": "Use CosmosDB for persistence", "reasoning": "Team expertise"})
    return tmp_path


class TestMnemoSearch:
    """mnemo_search routes to: search_memory, search_api, search_errors, cross_search."""

    def test_scope_memory(self, repo):
        result = handle_tool_call("mnemo_search", {"repo_path": str(repo), "query": "Redis", "scope": "memory"})
        assert not result.get("isError")
        assert "Redis" in result["content"][0]["text"]

    def test_scope_errors(self, repo):
        # Store an error first
        handle_tool_call("mnemo_record", {"repo_path": str(repo), "type": "error", "action": "add", "error": "NullRef in auth", "cause": "missing check", "fix": "added guard"})
        result = handle_tool_call("mnemo_search", {"repo_path": str(repo), "query": "NullRef", "scope": "errors"})
        assert not result.get("isError")

    def test_scope_all_default(self, repo):
        result = handle_tool_call("mnemo_search", {"repo_path": str(repo), "query": "Redis"})
        assert not result.get("isError")
        text = result["content"][0]["text"]
        assert len(text) > 0

    def test_scope_code(self, repo):
        result = handle_tool_call("mnemo_search", {"repo_path": str(repo), "query": "function", "scope": "code"})
        assert not result.get("isError")


class TestMnemoAudit:
    """mnemo_audit routes to: check_security, dead_code, drift, health, breaking_changes, check_conventions."""

    def test_report_health(self, repo):
        result = handle_tool_call("mnemo_audit", {"repo_path": str(repo), "report": "health"})
        assert not result.get("isError")
        assert "Health" in result["content"][0]["text"] or "health" in result["content"][0]["text"].lower()

    def test_report_security(self, repo):
        result = handle_tool_call("mnemo_audit", {"repo_path": str(repo), "report": "security"})
        assert not result.get("isError")

    def test_report_dead_code(self, repo):
        result = handle_tool_call("mnemo_audit", {"repo_path": str(repo), "report": "dead-code"})
        assert not result.get("isError")

    def test_report_drift(self, repo):
        result = handle_tool_call("mnemo_audit", {"repo_path": str(repo), "report": "drift"})
        assert not result.get("isError")

    def test_report_conventions(self, repo):
        result = handle_tool_call("mnemo_audit", {"repo_path": str(repo), "report": "conventions"})
        assert not result.get("isError")

    def test_report_breaking(self, repo):
        result = handle_tool_call("mnemo_audit", {"repo_path": str(repo), "report": "breaking"})
        assert not result.get("isError")

    def test_report_full(self, repo):
        result = handle_tool_call("mnemo_audit", {"repo_path": str(repo), "report": "full"})
        assert not result.get("isError")
        # Full report should contain multiple sections
        assert len(result["content"][0]["text"]) > 100


class TestMnemoRecord:
    """mnemo_record routes to: add_error, search_errors, add_incident, incidents, add_review, reviews, add_correction, corrections."""

    def test_add_error(self, repo):
        result = handle_tool_call("mnemo_record", {"repo_path": str(repo), "type": "error", "action": "add", "error": "TimeoutException in API", "cause": "slow DB query", "fix": "added index"})
        assert not result.get("isError")
        assert "stored" in result["content"][0]["text"].lower() or "error" in result["content"][0]["text"].lower()

    def test_search_errors(self, repo):
        handle_tool_call("mnemo_record", {"repo_path": str(repo), "type": "error", "action": "add", "error": "Connection refused", "cause": "port blocked", "fix": "opened firewall"})
        result = handle_tool_call("mnemo_record", {"repo_path": str(repo), "type": "error", "action": "search", "query": "Connection"})
        assert not result.get("isError")

    def test_add_incident(self, repo):
        result = handle_tool_call("mnemo_record", {"repo_path": str(repo), "type": "incident", "action": "add", "title": "Redis outage", "what_happened": "Redis crashed", "root_cause": "OOM", "fix": "increased memory"})
        assert not result.get("isError")

    def test_list_incidents(self, repo):
        handle_tool_call("mnemo_record", {"repo_path": str(repo), "type": "incident", "action": "add", "title": "DB failover", "what_happened": "Primary went down", "root_cause": "disk full", "fix": "cleanup"})
        result = handle_tool_call("mnemo_record", {"repo_path": str(repo), "type": "incident", "action": "list"})
        assert not result.get("isError")

    def test_add_review(self, repo):
        result = handle_tool_call("mnemo_record", {"repo_path": str(repo), "type": "review", "action": "add", "summary": "Reviewed auth refactor"})
        assert not result.get("isError")

    def test_add_correction(self, repo):
        result = handle_tool_call("mnemo_record", {"repo_path": str(repo), "type": "correction", "action": "add", "suggestion": "Use var", "correction": "Use const"})
        assert not result.get("isError")

    def test_list_corrections(self, repo):
        handle_tool_call("mnemo_record", {"repo_path": str(repo), "type": "correction", "action": "add", "suggestion": "Use any", "correction": "Use specific type"})
        result = handle_tool_call("mnemo_record", {"repo_path": str(repo), "type": "correction", "action": "list"})
        assert not result.get("isError")


class TestMnemoGenerate:
    """mnemo_generate routes to: commit_message, pr_description."""

    def test_generate_commit(self, repo):
        result = handle_tool_call("mnemo_generate", {"repo_path": str(repo), "target": "commit"})
        assert not result.get("isError")

    def test_generate_pr(self, repo):
        result = handle_tool_call("mnemo_generate", {"repo_path": str(repo), "target": "pr"})
        assert not result.get("isError")


class TestMnemoAsk:
    """mnemo_ask routes natural language to internal tools."""

    def test_ask_architecture(self, repo):
        result = handle_tool_call("mnemo_ask", {"repo_path": str(repo), "query": "what is the architecture of this project?"})
        assert not result.get("isError")
        assert len(result["content"][0]["text"]) > 0

    def test_ask_health(self, repo):
        result = handle_tool_call("mnemo_ask", {"repo_path": str(repo), "query": "what is the code health?"})
        assert not result.get("isError")

    def test_ask_security(self, repo):
        result = handle_tool_call("mnemo_ask", {"repo_path": str(repo), "query": "are there any security vulnerabilities?"})
        assert not result.get("isError")

    def test_ask_plan(self, repo):
        result = handle_tool_call("mnemo_ask", {"repo_path": str(repo), "query": "what is the plan status?"})
        assert not result.get("isError")

    def test_ask_history(self, repo):
        handle_tool_call("mnemo_record", {"repo_path": str(repo), "type": "error", "action": "add", "error": "StackOverflow", "cause": "recursion", "fix": "added base case"})
        result = handle_tool_call("mnemo_ask", {"repo_path": str(repo), "query": "have we seen StackOverflow errors before?"})
        assert not result.get("isError")

    def test_ask_general_lookup(self, repo):
        result = handle_tool_call("mnemo_ask", {"repo_path": str(repo), "query": "tell me about Collections class"})
        assert not result.get("isError")


class TestMnemoPlan:
    """mnemo_plan handles: create, status, done, add, remove, task, task_done."""

    def test_create_plan(self, repo):
        result = handle_tool_call("mnemo_plan", {"repo_path": str(repo), "action": "create", "title": "Migrate DB", "tasks": ["backup data", "run migration", "verify"]})
        assert not result.get("isError")

    def test_plan_status(self, repo):
        handle_tool_call("mnemo_plan", {"repo_path": str(repo), "action": "create", "title": "Test Plan", "tasks": ["step 1", "step 2"]})
        result = handle_tool_call("mnemo_plan", {"repo_path": str(repo), "action": "status"})
        assert not result.get("isError")
        assert "Test Plan" in result["content"][0]["text"]

    def test_set_task(self, repo):
        result = handle_tool_call("mnemo_plan", {"repo_path": str(repo), "action": "task", "task_id": "JIRA-123", "description": "Fix login bug"})
        assert not result.get("isError")

    def test_task_done(self, repo):
        handle_tool_call("mnemo_plan", {"repo_path": str(repo), "action": "task", "task_id": "JIRA-456", "description": "Add tests"})
        result = handle_tool_call("mnemo_plan", {"repo_path": str(repo), "action": "task_done", "task_id": "JIRA-456", "summary": "Added 10 tests"})
        assert not result.get("isError")


class TestCoreTools:
    """Direct core tools work correctly."""

    def test_recall(self, repo):
        result = handle_tool_call("mnemo_recall", {"repo_path": str(repo)})
        assert not result.get("isError")
        assert "Redis" in result["content"][0]["text"] or "CosmosDB" in result["content"][0]["text"]

    def test_remember_and_search(self, repo):
        handle_tool_call("mnemo_remember", {"repo_path": str(repo), "content": "Always use async/await for DB calls", "category": "preference"})
        result = handle_tool_call("mnemo_search", {"repo_path": str(repo), "query": "async database", "scope": "memory"})
        assert not result.get("isError")

    def test_decide(self, repo):
        result = handle_tool_call("mnemo_decide", {"repo_path": str(repo), "decision": "Use PostgreSQL for analytics", "reasoning": "Better for OLAP"})
        assert not result.get("isError")
        assert "recorded" in result["content"][0]["text"].lower()

    def test_forget(self, repo):
        handle_tool_call("mnemo_remember", {"repo_path": str(repo), "content": "temporary note to delete"})
        result = handle_tool_call("mnemo_forget", {"repo_path": str(repo), "memory_id": "3"})
        assert not result.get("isError")

    @pytest.mark.skip(reason="Legacy graph.json replaced by LadybugDB engine - new MCP tools pending")
    def test_graph_stats(self, repo):
        result = handle_tool_call("mnemo_graph", {"repo_path": str(repo), "action": "stats"})
        assert not result.get("isError")
        assert "Nodes" in result["content"][0]["text"]

    def test_lesson_add(self, repo):
        result = handle_tool_call("mnemo_lesson", {"repo_path": str(repo), "action": "add", "content": "Always check for null before accessing nested properties"})
        assert not result.get("isError")

    def test_lesson_list(self, repo):
        handle_tool_call("mnemo_lesson", {"repo_path": str(repo), "action": "add", "content": "Use parameterized queries to prevent SQL injection"})
        result = handle_tool_call("mnemo_lesson", {"repo_path": str(repo), "action": "list"})
        assert not result.get("isError")

    def test_context(self, repo):
        result = handle_tool_call("mnemo_context", {"repo_path": str(repo), "context": {"framework": "FastAPI", "db": "PostgreSQL"}})
        assert not result.get("isError")

    def test_map(self, repo):
        result = handle_tool_call("mnemo_map", {"repo_path": str(repo)})
        assert not result.get("isError")
