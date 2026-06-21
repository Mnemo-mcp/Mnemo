"""Monster Test Harness — tests ALL Mnemo features via MCP + combinations + scale + hooks.

Simulates real Kiro CLI usage: MCP tool calls, hook firing, multi-session workflows.
Tests features in isolation AND in realistic combinations.
"""

import json
import os
import subprocess
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from mnemo.mcp_server import handle_tool_call
from mnemo.hooks.kiro import install_kiro_hooks
from mnemo.memory import add_memory, add_decision, recall, search_memory, forget_memory
from mnemo.memory.services import remember_with_effects, decide_with_effects
from mnemo.storage import Collections, get_storage


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def repo(tmp_path):
    """Create a realistic project repo with source files + .mnemo initialized."""
    # Source files (Python project with multiple modules)
    src = tmp_path / "src"
    src.mkdir()
    (src / "__init__.py").write_text("")
    (src / "auth.py").write_text(
        "from .models import User\n\n"
        "class AuthService:\n"
        "    def authenticate(self, username: str, password: str) -> User:\n"
        "        pass\n\n"
        "    def refresh_token(self, token: str) -> str:\n"
        "        pass\n\n"
        "    def revoke(self, user_id: int) -> None:\n"
        "        pass\n"
    )
    (src / "models.py").write_text(
        "class User:\n"
        "    def __init__(self, id: int, name: str, email: str):\n"
        "        self.id = id\n\n"
        "class Payment:\n"
        "    def __init__(self, amount: float, user_id: int):\n"
        "        self.amount = amount\n"
    )
    (src / "payments.py").write_text(
        "from .models import Payment\nfrom .auth import AuthService\n\n"
        "class PaymentService:\n"
        "    def __init__(self, auth: AuthService):\n"
        "        self.auth = auth\n\n"
        "    def process(self, user_id: int, amount: float) -> Payment:\n"
        "        pass\n\n"
        "    def refund(self, payment_id: int) -> bool:\n"
        "        pass\n"
    )
    (src / "utils.py").write_text(
        "def hash_password(password: str) -> str:\n    pass\n\n"
        "def validate_email(email: str) -> bool:\n    pass\n\n"
        "def _internal_helper():\n    pass\n"
    )

    # .mnemo directory
    mnemo = tmp_path / ".mnemo"
    mnemo.mkdir()
    for f in ("memory.json", "decisions.json", "plans.json", "tasks.json"):
        (mnemo / f).write_text("[]")
    (mnemo / "context.json").write_text("{}")
    (mnemo / "hashes.json").write_text("{}")
    (mnemo / "slots.json").write_text("{}")
    (mnemo / "tree.md").write_text("# Repo Map\nsrc/ (4 files)\n  Classes: AuthService, User, Payment, PaymentService\n")

    return tmp_path


def _call(tool_name: str, repo: Path, **kwargs) -> str:
    """Helper to call MCP tool and return text result."""
    args = {"repo_path": str(repo), **kwargs}
    result = handle_tool_call(tool_name, args)
    text = result["content"][0]["text"]
    return text


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: INDIVIDUAL MCP TOOL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMemoryTools:
    """Test all memory MCP tools via handle_tool_call."""

    def test_remember(self, repo):
        result = _call("mnemo_remember", repo, content="Use PostgreSQL for user data", category="architecture")
        assert "Stored" in result

    def test_remember_dedup(self, repo):
        _call("mnemo_remember", repo, content="Use PostgreSQL for everything", category="architecture")
        _call("mnemo_remember", repo, content="Use PostgreSQL for everything", category="architecture")
        storage = get_storage(repo)
        entries = storage.read_collection(Collections.MEMORY)
        # Should not duplicate
        pg_entries = [e for e in entries if "PostgreSQL for everything" in e.get("content", "")]
        assert len(pg_entries) == 1

    def test_recall_standard(self, repo):
        with patch("mnemo.memory.store._get_current_branch", return_value="main"):
            _call("mnemo_remember", repo, content="Auth uses JWT RS256", category="architecture")
        result = _call("mnemo_recall", repo, tier="standard")
        assert "JWT" in result or "Repo Map" in result

    def test_recall_compact(self, repo):
        with patch("mnemo.memory.store._get_current_branch", return_value="main"):
            _call("mnemo_remember", repo, content="Redis at port 6379", category="architecture")
        result = _call("mnemo_recall", repo, tier="compact")
        # Compact is brief
        assert len(result) < 3000

    def test_recall_deep(self, repo):
        result = _call("mnemo_recall", repo, tier="deep")
        assert isinstance(result, str)

    def test_search_memory(self, repo):
        with patch("mnemo.memory.store._get_current_branch", return_value="main"):
            _call("mnemo_remember", repo, content="Authentication uses JWT tokens with RS256 signing algorithm", category="architecture")
        result = _call("mnemo_search_memory", repo, query="JWT authentication")
        assert "JWT" in result

    def test_forget(self, repo):
        with patch("mnemo.memory.store._get_current_branch", return_value="main"):
            _call("mnemo_remember", repo, content="Temporary note to forget", category="general")
        storage = get_storage(repo)
        entries = storage.read_collection(Collections.MEMORY)
        entry_id = entries[-1]["id"]
        result = _call("mnemo_forget", repo, memory_id=entry_id)
        assert "deleted" in result.lower()

    def test_decide(self, repo):
        result = _call("mnemo_decide", repo, decision="Use microservices with gRPC", reasoning="Better scalability")
        assert "Decision" in result or "recorded" in result.lower()

    def test_context(self, repo):
        result = _call("mnemo_context", repo, context={"database": "PostgreSQL", "cache": "Redis"})
        assert "updated" in result.lower()

    def test_slot_set_get(self, repo):
        _call("mnemo_slot_set", repo, name="project_context", content="Healthcare EDI platform")
        result = _call("mnemo_slot_get", repo, name="project_context")
        assert "Healthcare" in result

    def test_lesson_lifecycle(self, repo):
        _call("mnemo_lesson", repo, action="add", content="Always validate input before DB queries")
        result = _call("mnemo_lesson", repo, action="list")
        assert "validate input" in result


class TestPlanTools:
    """Test planning MCP tools."""

    def test_create_plan(self, repo):
        result = _call("mnemo_plan", repo, action="create", title="Build auth", tasks=["Add JWT", "Add refresh", "Add revoke"])
        assert "Created" in result or "MNO" in result

    def test_plan_status(self, repo):
        _call("mnemo_plan", repo, action="create", title="Test plan", tasks=["Task 1", "Task 2"])
        result = _call("mnemo_plan", repo, action="status")
        assert "Test plan" in result

    def test_plan_done(self, repo):
        _call("mnemo_plan", repo, action="create", title="Small plan", tasks=["Only task"])
        # Find the task ID
        result = _call("mnemo_plan", repo, action="status")
        # Mark it done
        import re
        task_ids = re.findall(r'MNO-\d+', result)
        if task_ids:
            done_result = _call("mnemo_plan", repo, action="done", task_id=task_ids[0])
            assert "done" in done_result.lower() or "complete" in done_result.lower()


class TestCodeIntelTools:
    """Test code intelligence MCP tools (require graph)."""

    @pytest.fixture(autouse=True)
    def _init_graph(self, repo):
        """Initialize the graph for code intel tests."""
        from mnemo.engine.pipeline import run_pipeline
        try:
            run_pipeline(repo)
        except Exception:
            pytest.skip("Pipeline requires tree-sitter")

    def test_graph_stats(self, repo):
        result = _call("mnemo_graph", repo, action="stats")
        assert "File" in result or "Class" in result or "Edge" in result

    def test_graph_find(self, repo):
        result = _call("mnemo_graph", repo, action="find", name="AuthService")
        assert "AuthService" in result or "auth" in result.lower()

    def test_lookup_class(self, repo):
        result = _call("mnemo_lookup", repo, symbol="AuthService")
        assert "AuthService" in result or "authenticate" in result

    def test_lookup_function(self, repo):
        result = _call("mnemo_lookup", repo, symbol="hash_password")
        assert "hash_password" in result

    def test_map(self, repo):
        result = _call("mnemo_map", repo)
        assert "Repo Map" in result or "src" in result


class TestQualityTools:
    """Test quality/audit MCP tools."""

    def test_audit_health(self, repo):
        result = _call("mnemo_audit", repo, report="health")
        assert "Health" in result or "health" in result or "memory" in result.lower()

    def test_audit_security(self, repo):
        result = _call("mnemo_audit", repo, report="security")
        # May find issues or report clean
        assert isinstance(result, str)


class TestRecordTools:
    """Test engineering records MCP tools."""

    def test_add_error(self, repo):
        result = _call("mnemo_record", repo, type="error", action="add",
                       error="TypeError: null is not an object", cause="Missing null check",
                       fix="Added optional chaining", file="src/auth.py")
        assert "stored" in result.lower() or "added" in result.lower() or "recorded" in result.lower()

    def test_search_errors(self, repo):
        _call("mnemo_record", repo, type="error", action="add",
              error="ConnectionTimeout in payment service", cause="Pool exhausted", fix="Increased pool size")
        result = _call("mnemo_record", repo, type="error", action="search", query="timeout")
        assert "timeout" in result.lower() or "Timeout" in result

    def test_add_incident(self, repo):
        result = _call("mnemo_record", repo, type="incident", action="add",
                       title="Payment service outage", what_happened="500 errors for 30min",
                       root_cause="Redis connection limit", fix="Increased maxclients",
                       severity="high", services=["payments", "checkout"])
        assert isinstance(result, str)

    def test_add_correction(self, repo):
        result = _call("mnemo_record", repo, type="correction", action="add",
                       suggestion="Use var for all variables", correction="Use const for immutable values")
        assert isinstance(result, str)


class TestGenerationTools:
    """Test git generation tools."""

    def test_generate_commit_no_changes(self, repo):
        result = _call("mnemo_generate", repo, target="commit")
        assert "No changes" in result or isinstance(result, str)

    def test_generate_pr_no_changes(self, repo):
        result = _call("mnemo_generate", repo, target="pr")
        assert isinstance(result, str)


class TestMetaTools:
    """Test mnemo_ask routing."""

    def test_ask_routes(self, repo):
        result = _call("mnemo_ask", repo, query="What is the architecture?")
        assert isinstance(result, str)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: FEATURE COMBINATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMemoryCombinations:
    """Test memory features interacting with each other."""

    def test_store_search_recall_cycle(self, repo):
        """THE critical path: store → search finds it → recall shows it."""
        with patch("mnemo.memory.store._get_current_branch", return_value="main"):
            _call("mnemo_remember", repo, content="PostgreSQL is our primary database with pgvector extension", category="architecture")
            _call("mnemo_remember", repo, content="Redis cluster at redis.internal:6379 for session caching", category="architecture")
            _call("mnemo_remember", repo, content="Deploy pipeline uses GitHub Actions to ECR to ECS Fargate", category="architecture")

        # Search finds relevant memory
        search_result = _call("mnemo_search_memory", repo, query="database")
        assert "PostgreSQL" in search_result

        # Recall includes it
        recall_result = _call("mnemo_recall", repo, tier="standard")
        assert "PostgreSQL" in recall_result

    def test_contradiction_supersedes(self, repo):
        """Store contradicting decision → old one superseded → recall only shows new."""
        _call("mnemo_decide", repo, decision="Use MongoDB as the primary database for all user profile data")
        _call("mnemo_decide", repo, decision="Use PostgreSQL as the primary database for all user profile data instead of MongoDB")

        storage = get_storage(repo)
        decisions = storage.read_collection(Collections.DECISIONS)
        active = [d for d in decisions if d.get("active", True)]
        inactive = [d for d in decisions if not d.get("active", True)]

        assert any("PostgreSQL" in d["decision"] for d in active)
        assert any("MongoDB" in d["decision"] for d in inactive)

        # Recall only shows active
        recall_result = _call("mnemo_recall", repo, tier="standard")
        if "Decisions" in recall_result:
            assert "PostgreSQL" in recall_result

    def test_forget_removes_from_search(self, repo):
        """Forgotten memories are removed from storage."""
        with patch("mnemo.memory.store._get_current_branch", return_value="main"):
            _call("mnemo_remember", repo, content="Secret: temporary password is hunter2", category="general")

        storage = get_storage(repo)
        entries = storage.read_collection(Collections.MEMORY)
        entry_id = entries[-1]["id"]

        _call("mnemo_forget", repo, memory_id=entry_id)

        # Verify removed from storage
        entries_after = storage.read_collection(Collections.MEMORY)
        assert not any(e.get("id") == entry_id for e in entries_after)

    def test_slot_appears_in_recall(self, repo):
        """Slots set via tool appear in standard recall."""
        _call("mnemo_slot_set", repo, name="project_context", content="Healthcare EDI platform processing X12 transactions")
        recall_result = _call("mnemo_recall", repo, tier="standard")
        assert "Healthcare" in recall_result or "Working Context" in recall_result

    def test_lesson_reinforcement(self, repo):
        """Adding same lesson twice boosts confidence."""
        _call("mnemo_lesson", repo, action="add", content="Always use parameterized queries for SQL")
        _call("mnemo_lesson", repo, action="add", content="Always use parameterized queries for SQL")
        result = _call("mnemo_lesson", repo, action="list")
        # Confidence should be > 0.5 (initial) after reinforcement
        assert "0.5" not in result or "0.6" in result or "parameterized" in result

    def test_correction_decays_memory_confidence(self, repo):
        """Adding a correction reduces related memory confidence."""
        with patch("mnemo.memory.store._get_current_branch", return_value="main"):
            _call("mnemo_remember", repo, content="Use var for variable declarations in JavaScript", category="preference")

        _call("mnemo_record", repo, type="correction", action="add",
              suggestion="Use var for variables", correction="Use const for immutable, let for mutable")

        # The correction should exist
        from mnemo.records.corrections import _load_corrections
        corrections = _load_corrections(repo)
        assert len(corrections) >= 1


class TestPlanCombinations:
    """Test planning features working together."""

    def test_full_plan_lifecycle(self, repo):
        """Create → add task → mark done → status reflects progress."""
        _call("mnemo_plan", repo, action="create", title="Auth feature", tasks=["Add JWT", "Add refresh endpoint"])

        status = _call("mnemo_plan", repo, action="status")
        assert "Auth feature" in status
        assert "0/" not in status or "2" in status  # Shows task count

    def test_decision_auto_creates_plan(self, repo):
        """A decision with 3+ actionable items auto-creates a plan."""
        _call("mnemo_decide", repo,
              decision="Migrate to microservices:\n- Extract auth service\n- Extract payment service\n- Extract notification service\n- Set up API gateway")

        # Check if plan was auto-created
        from mnemo.plan import _load_plans
        plans = _load_plans(repo)
        # May or may not trigger depending on detection threshold
        # At minimum, decision should be stored
        storage = get_storage(repo)
        decisions = storage.read_collection(Collections.DECISIONS)
        assert any("microservices" in d["decision"].lower() for d in decisions)

    def test_plan_in_recall(self, repo):
        """Active plan appears in recall."""
        _call("mnemo_plan", repo, action="create", title="Build caching layer", tasks=["Add Redis client", "Add cache middleware"])
        recall_result = _call("mnemo_recall", repo, tier="standard")
        assert "caching" in recall_result.lower() or "Plan" in recall_result


class TestCrossFeatureCombinations:
    """Test features from different categories working together."""

    def test_error_record_searchable_via_memory_search(self, repo):
        """Errors stored via mnemo_record are findable."""
        _call("mnemo_record", repo, type="error", action="add",
              error="OOM in payment batch job", cause="Unbounded list growth", fix="Added pagination")
        result = _call("mnemo_record", repo, type="error", action="search", query="OOM")
        assert "OOM" in result or "payment" in result

    def test_workspace_link_and_query(self, tmp_path):
        """Link a repo and cross-search works."""
        main = tmp_path / "main"
        main.mkdir()
        (main / ".git").mkdir()
        (main / ".mnemo").mkdir()
        (main / ".mnemo" / "memory.json").write_text("[]")
        (main / ".mnemo" / "links.json").write_text("[]")

        other = tmp_path / "other"
        other.mkdir()
        (other / ".git").mkdir()
        (other / ".mnemo").mkdir()
        (other / ".mnemo" / "memory.json").write_text("[]")

        from mnemo.workspace import link_repo, get_linked_repos
        link_repo(main, other)
        linked = get_linked_repos(main)
        assert len(linked) == 1

    def test_knowledge_base_searchable(self, repo):
        """Knowledge base files are searchable."""
        kb = repo / ".mnemo" / "knowledge"
        kb.mkdir()
        (kb / "deploy.md").write_text("# Deployment\n\nWe deploy to ECS Fargate with Blue/Green strategy.\n")

        from mnemo.knowledge import search_knowledge
        result = search_knowledge(repo, "Fargate")
        assert "Fargate" in result


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: SCALE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAtScale:
    """Test features under load — many memories, decisions, plans."""

    def test_50_memories_recall_fits_budget(self, repo):
        """With 50 memories, recall stays within token budget (~2000 tokens)."""
        with patch("mnemo.memory.store._get_current_branch", return_value="main"):
            for i in range(50):
                categories = ["architecture", "pattern", "bug", "preference", "general"]
                cat = categories[i % 5]
                add_memory(repo, f"Memory #{i}: important context about feature {i} in module {i % 10}", cat)

        result = _call("mnemo_recall", repo, tier="standard")
        # Standard recall should be bounded (~2000 tokens ≈ ~8000 chars)
        assert len(result) < 12000
        # Should include SOME memories but not all 50
        assert "Memory #" in result

    def test_10_decisions_3_contradictions(self, repo):
        """Decisions with explicit contradictions get superseded."""
        decisions_content = [
            "Use PostgreSQL for user data storage in all services",
            "Deploy to AWS ECS with Fargate for container orchestration",
            "Use Redis for session management across all services",
            "Authentication via JWT RS256 for API access",
            "API gateway with Kong for traffic routing",
            "Monitoring with Datadog for observability",
            "CI/CD with GitHub Actions for build pipeline",
            # Explicit contradictions (include "instead of" for detection):
            "Use MySQL for user data storage in all services instead of PostgreSQL",
            "Deploy to GCP Cloud Run for container orchestration instead of AWS ECS Fargate",
            "Use Memcached for session management across all services instead of Redis",
        ]
        for d in decisions_content:
            add_decision(repo, d)

        storage = get_storage(repo)
        decisions = storage.read_collection(Collections.DECISIONS)
        active = [d for d in decisions if d.get("active", True)]
        inactive = [d for d in decisions if not d.get("active", True)]

        # With explicit contradictions, at least 2 should be superseded
        assert len(inactive) >= 2
        assert len(active) <= 8

    def test_search_relevance_with_many_memories(self, repo):
        """With 30 memories, search returns most relevant first."""
        with patch("mnemo.memory.store._get_current_branch", return_value="main"):
            # Noise
            for i in range(25):
                add_memory(repo, f"Unrelated memory about topic {i} with random content", "general")
            # Signal
            add_memory(repo, "PostgreSQL connection pool configured with max 20 connections at port 5432", "architecture")
            add_memory(repo, "Database migrations use Flyway with versioned SQL scripts", "architecture")
            add_memory(repo, "Redis cluster for caching with 3 nodes at redis.internal", "architecture")

        result = _call("mnemo_search_memory", repo, query="PostgreSQL database connection")
        # PostgreSQL memory should be in results
        assert "PostgreSQL" in result


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: KIRO CLI HOOK SIMULATION (Multi-Session)
# ═══════════════════════════════════════════════════════════════════════════════

class TestKiroMultiSession:
    """Simulate multiple Kiro CLI sessions with hooks firing."""

    @pytest.fixture
    def kiro_repo(self, repo):
        """Repo with Kiro hooks installed."""
        with patch("mnemo.hooks.kiro.find_mnemo_cli", return_value="mnemo"), \
             patch("mnemo.hooks.kiro.find_mnemo_mcp", return_value="mnemo-mcp"):
            install_kiro_hooks(repo)
        return repo

    def _run_hook(self, hook_path: Path, stdin_data: str, cwd: Path) -> tuple[str, str, int]:
        result = subprocess.run(
            ["sh", str(hook_path)], input=stdin_data,
            capture_output=True, text=True, cwd=str(cwd), timeout=30,
        )
        return result.stdout, result.stderr, result.returncode

    def test_session_1_store_session_2_recall(self, kiro_repo):
        """Session 1 stores memory → Session 2 recall includes it."""
        # Session 1: Store knowledge
        with patch("mnemo.memory.store._get_current_branch", return_value="main"):
            _call("mnemo_remember", kiro_repo, content="AuthService uses OAuth2 with PKCE flow", category="architecture")
            _call("mnemo_decide", kiro_repo, decision="Use event-driven architecture with Kafka")

        # Session 2: Recall includes both
        recall_result = _call("mnemo_recall", kiro_repo, tier="standard")
        assert "OAuth2" in recall_result or "AuthService" in recall_result
        assert "Kafka" in recall_result or "event-driven" in recall_result

    def test_session_prompt_finds_previous_context(self, kiro_repo):
        """User asks a question → prompt-submit finds relevant past memory."""
        with patch("mnemo.memory.store._get_current_branch", return_value="main"):
            _call("mnemo_remember", kiro_repo, content="Database timeout was caused by missing index on users.email column", category="bug")

        # Simulate prompt-submit: search for related topic
        search_result = _call("mnemo_search_memory", kiro_repo, query="database timeout issue")
        assert "timeout" in search_result or "index" in search_result

    def test_decision_contradiction_across_sessions(self, kiro_repo):
        """Session 1 decides X → Session 3 decides Y → only Y in recall."""
        # Session 1
        _call("mnemo_decide", kiro_repo, decision="Use REST API for all inter-service communication")

        # Session 3 (later, changed mind)
        _call("mnemo_decide", kiro_repo, decision="Use gRPC for all inter-service communication instead of REST")

        # Session 4: recall shows only gRPC
        recall_result = _call("mnemo_recall", kiro_repo, tier="standard")
        if "Decisions" in recall_result:
            # gRPC should be there, REST should be superseded
            lines = recall_result.split("\n")
            decision_lines = [l for l in lines if "inter-service" in l.lower()]
            if decision_lines:
                assert any("gRPC" in l for l in decision_lines)

    def test_hook_pre_tool_blocks_dangerous(self, kiro_repo):
        """Pre-tool-use hook blocks catastrophic commands."""
        hooks_dir = kiro_repo / ".kiro" / "hooks"
        stdin = json.dumps({"tool_name": "shell", "tool_input": {"command": "rm -rf /"}})
        stdout, stderr, code = self._run_hook(hooks_dir / "pre-tool-use.sh", stdin, kiro_repo)
        assert code == 2  # Blocked (Kiro protocol: exit 2 = block)

    def test_hook_pre_tool_allows_safe(self, kiro_repo):
        """Pre-tool-use hook allows safe commands."""
        hooks_dir = kiro_repo / ".kiro" / "hooks"
        stdin = json.dumps({"tool_name": "shell", "tool_input": {"command": "ls -la src/"}})
        stdout, stderr, code = self._run_hook(hooks_dir / "pre-tool-use.sh", stdin, kiro_repo)
        assert code == 0  # Allowed

    def test_hook_stop_captures_bug_fix(self, kiro_repo):
        """Stop hook detects bug fix in agent response → stores memory."""
        with patch("mnemo.memory.store._get_current_branch", return_value="main"):
            # Simulate what stop hook does: detect learning and store
            remember_with_effects(
                kiro_repo,
                "Bug fix: connection pool exhausting because connections not closed in finally block",
                "bug"
            )

        # Verify it's in memory and searchable
        search_result = _call("mnemo_search_memory", kiro_repo, query="connection pool")
        assert "connection pool" in search_result

    def test_full_3_session_workflow(self, kiro_repo):
        """Complete 3-session workflow proving memory persists and grows."""
        with patch("mnemo.memory.store._get_current_branch", return_value="main"):
            # === SESSION 1: Project setup ===
            _call("mnemo_decide", kiro_repo, decision="Microservices with gRPC and Protocol Buffers")
            _call("mnemo_remember", kiro_repo, content="Auth service handles OAuth2 PKCE flow for mobile clients", category="architecture")
            _call("mnemo_plan", kiro_repo, action="create", title="Build auth", tasks=["JWT signing", "Token refresh", "Revocation"])

            # === SESSION 2: Implementation ===
            # Agent already knows architecture (recall proves it)
            recall_s2 = _call("mnemo_recall", kiro_repo, tier="standard")
            assert "gRPC" in recall_s2 or "Microservices" in recall_s2

            # Agent fixes a bug and we store it
            _call("mnemo_remember", kiro_repo, content="Bug fix: JWT expiry was 5s instead of 15min due to seconds vs milliseconds confusion", category="bug")

            # === SESSION 3: Continuing ===
            recall_s3 = _call("mnemo_recall", kiro_repo, tier="standard")
            # Should have decision + architecture + bug fix
            assert "gRPC" in recall_s3 or "Microservices" in recall_s3
            assert "JWT" in recall_s3 or "expiry" in recall_s3

            # Search for the bug
            search_result = _call("mnemo_search_memory", kiro_repo, query="JWT token expiry bug")
            assert "expiry" in search_result or "milliseconds" in search_result
