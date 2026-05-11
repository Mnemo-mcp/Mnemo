#!/usr/bin/env python3
"""
Mnemo Tool Test Suite — exercises every MCP tool against a real repo.
Usage: python3 test_all_tools.py [repo_path]
Default repo: /Users/nikhil.tiwari/CodeRepo/MockUIRemoval/Mock_Payer
"""

import json
import sys
import time
from pathlib import Path

# Add mnemo to path
sys.path.insert(0, str(Path(__file__).parent))

from mnemo.mcp_server import handle_tool_call, TOOLS

REPO = sys.argv[1] if len(sys.argv) > 1 else "/Users/nikhil.tiwari/CodeRepo/MockUIRemoval/Mock_Payer"

# Test cases: (tool_name, arguments, description, expected_substring_or_None)
TEST_CASES = [
    # --- Memory & Context ---
    ("mnemo_recall", {}, "Recall project context", "Project Context"),
    ("mnemo_remember", {"content": "TEST: Mock_Payer uses C# microservices with ASP.NET Core", "category": "architecture"}, "Store a memory", "Stored memory"),
    ("mnemo_search_memory", {"query": "microservices"}, "Search memory semantically", None),
    ("mnemo_decide", {"decision": "TEST: Use Redis for session caching", "reasoning": "Low latency needed"}, "Record a decision", "Decision #"),
    ("mnemo_context", {"context": {"tech_stack": "C#, ASP.NET Core, Vue.js"}}, "Save project context", "Context updated"),
    ("mnemo_forget", {"memory_id": 1}, "Delete a memory by ID", None),

    # --- Code Understanding ---
    ("mnemo_lookup", {"query": "Controller"}, "Lookup controllers", None),
    ("mnemo_map", {}, "Regenerate repo map", "Repo map regenerated"),
    ("mnemo_intelligence", {}, "Generate intelligence report", None),
    ("mnemo_similar", {"query": "Service"}, "Find similar implementations", None),
    ("mnemo_context_for_task", {"query": "eligibility"}, "Get task-scoped context", None),

    # --- Knowledge & APIs ---
    ("mnemo_knowledge", {}, "List knowledge base", None),
    ("mnemo_knowledge", {"query": "architecture"}, "Search knowledge base", None),
    ("mnemo_discover_apis", {}, "Discover API endpoints", None),
    ("mnemo_search_api", {"query": "eligibility"}, "Search for an API", None),

    # --- Code Review ---
    ("mnemo_add_review", {"summary": "TEST: Reviewed IsAuthRequired controller", "files": ["isAuthRequiredService/Controllers/IsAuthRequiredController.cs"], "feedback": "Good separation of concerns", "outcome": "approved"}, "Store a review", "Review #"),
    ("mnemo_reviews", {}, "List reviews", None),

    # --- Error Memory ---
    ("mnemo_add_error", {"error": "NullReferenceException in PayerHandler", "cause": "Payer config not loaded", "fix": "Added null check in BasePayerHandler", "file": "isAuthRequiredService/Services/PayerHandlers/BasePayerHandler.cs", "tags": ["null", "payer"]}, "Store an error", "Error #"),
    ("mnemo_search_errors", {"query": "NullReference"}, "Search errors", None),

    # --- Dependency Graph ---
    ("mnemo_dependencies", {}, "Show dependency graph", None),
    ("mnemo_impact", {"query": "IsAuthRequiredController"}, "Impact analysis", None),

    # --- Onboarding ---
    ("mnemo_onboarding", {}, "Generate onboarding guide", None),

    # --- Sprint/Task ---
    ("mnemo_task", {"task_id": "MOCK-101", "description": "Add new payer handler for UHC", "files": ["isAuthRequiredService/Services/PayerHandlers/"], "notes": "Follow AetnaHandler pattern"}, "Set active task", "Task MOCK-101"),
    ("mnemo_task", {}, "Get current task", "MOCK-101"),
    ("mnemo_task_done", {"task_id": "MOCK-101", "summary": "UHC handler implemented"}, "Complete task", None),

    # --- Test Intelligence ---
    ("mnemo_tests", {}, "Get coverage summary", None),
    ("mnemo_tests", {"query": "Controller"}, "Find tests for a file", None),

    # --- Code Health ---
    ("mnemo_health", {}, "Code health report", "Code Health"),

    # --- Team Graph ---
    ("mnemo_team", {}, "Team expertise map", None),
    ("mnemo_who_touched", {"query": "Program.cs"}, "Who last modified a file", None),

    # --- Incidents ---
    ("mnemo_add_incident", {"title": "TEST: Auth service 503 errors", "what_happened": "IsAuthRequired service returned 503 for 10 minutes", "root_cause": "CosmosDB throttling due to missing index", "fix": "Added composite index on payerId+timestamp", "prevention": "Set up RU alerts", "severity": "high", "services": ["isAuthRequiredService"]}, "Record incident", "Incident #"),
    ("mnemo_incidents", {}, "List incidents", None),
    ("mnemo_incidents", {"query": "503"}, "Search incidents", None),

    # --- Commit & PR ---
    ("mnemo_commit_message", {}, "Generate commit message", None),
    ("mnemo_pr_description", {}, "Generate PR description", None),

    # --- Dead Code ---
    ("mnemo_dead_code", {}, "Detect dead code", None),

    # --- Security ---
    ("mnemo_add_security_pattern", {"name": "TEST: Hardcoded connection string", "regex": r"AccountKey=[A-Za-z0-9+/=]{20,}", "severity": "high", "description": "CosmosDB keys in source"}, "Add security pattern", "Security pattern #"),
    ("mnemo_check_security", {}, "Run security scan", None),
    ("mnemo_check_security", {"file": "isAuthRequiredService/Program.cs"}, "Security scan single file", None),

    # --- Breaking Changes ---
    ("mnemo_breaking_changes", {"action": "baseline"}, "Save API baseline", None),
    ("mnemo_breaking_changes", {"action": "check"}, "Check breaking changes", None),

    # --- Regressions ---
    ("mnemo_add_regression", {"file": "isAuthRequiredService/Services/PayerHandlers/BasePayerHandler.cs", "bug": "NullRef when payer config missing", "fix": "Added null guard", "test": "test_base_handler_null_config"}, "Record regression risk", "Regression #"),
    ("mnemo_check_regressions", {}, "List all regressions", None),
    ("mnemo_check_regressions", {"file": "isAuthRequiredService/Services/PayerHandlers/BasePayerHandler.cs"}, "Check file regressions", None),

    # --- Architecture Drift ---
    ("mnemo_drift", {}, "Detect architecture drift", None),

    # --- Git Hooks ---
    ("mnemo_hooks_install", {}, "Install git hooks", None),
    ("mnemo_check", {}, "Run pre-commit check", None),

    # --- Corrections ---
    ("mnemo_add_correction", {"suggestion": "Use HttpClient directly", "correction": "Use IHttpClientFactory for DI", "context": "ASP.NET Core best practice", "file": "isAuthRequiredService/Services/ApimService.cs"}, "Store correction", "Correction #"),
    ("mnemo_corrections", {}, "List corrections", None),

    # --- Velocity ---
    ("mnemo_velocity", {}, "Show velocity metrics", None),

    # --- Multi-Repo ---
    ("mnemo_links", {}, "Show linked repos", None),
    ("mnemo_cross_search", {"query": "authorization", "namespace": "code"}, "Cross-repo search", None),
    ("mnemo_cross_impact", {"query": "IsAuthRequiredService"}, "Cross-repo impact", None),
]


def run_tests():
    """Run all tool tests and report results."""
    print(f"{'='*70}")
    print("  MNEMO TOOL TEST SUITE")
    print(f"  Repo: {REPO}")
    print(f"  Tools to test: {len(TEST_CASES)}")
    print(f"{'='*70}\n")

    passed = 0
    failed = 0
    errors = []
    timings = []

    for i, (tool, args, desc, expected) in enumerate(TEST_CASES, 1):
        args_with_path = {**args, "repo_path": REPO}
        start = time.time()
        try:
            result = handle_tool_call(tool, args_with_path)
            elapsed = time.time() - start
            timings.append((tool, elapsed))

            is_error = result.get("isError", False)
            text = result.get("content", [{}])[0].get("text", "")

            if is_error:
                status = "❌ FAIL (tool returned error)"
                failed += 1
                errors.append((tool, desc, text[:200]))
            elif expected and expected not in text:
                status = f"⚠️  WARN (expected '{expected}' not in output)"
                failed += 1
                errors.append((tool, desc, f"Expected '{expected}', got: {text[:100]}"))
            else:
                status = "✅ PASS"
                passed += 1

            # Truncate output for display
            preview = text[:80].replace("\n", " ")
            print(f"  [{i:02d}/{len(TEST_CASES)}] {status} | {tool}")
            print(f"         {desc}")
            print(f"         ⏱ {elapsed:.3f}s | {preview}...")
            print()

        except Exception as exc:
            elapsed = time.time() - start
            failed += 1
            errors.append((tool, desc, str(exc)[:200]))
            print(f"  [{i:02d}/{len(TEST_CASES)}] 💥 ERROR | {tool}")
            print(f"         {desc}")
            print(f"         Exception: {exc}")
            print()

    # Summary
    print(f"\n{'='*70}")
    print(f"  RESULTS: {passed} passed, {failed} failed, {len(TEST_CASES)} total")
    print(f"{'='*70}")

    if errors:
        print("\n  FAILURES:")
        for tool, desc, msg in errors:
            print(f"    ❌ {tool}: {desc}")
            print(f"       {msg}")
            print()

    # Slowest tools
    timings.sort(key=lambda x: x[1], reverse=True)
    print("\n  SLOWEST TOOLS (top 5):")
    for tool, t in timings[:5]:
        print(f"    {t:.3f}s — {tool}")

    print(f"\n  TOTAL TIME: {sum(t for _, t in timings):.2f}s")
    print()

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_tests())
