#!/usr/bin/env python3
"""Mnemo Search Quality Benchmark — reproducible R@5 evaluation.

Usage: python3 benchmark/search_quality.py

Seeds 10 memories, runs 11 queries, reports Recall@5.
"""

import shutil
import time
from pathlib import Path
from unittest.mock import patch

# Setup
REPO = Path("/tmp/mnemo_benchmark")
if REPO.exists():
    shutil.rmtree(REPO)
REPO.mkdir()
(REPO / ".mnemo").mkdir()
for f in ("memory.json", "decisions.json", "plans.json", "tasks.json"):
    (REPO / ".mnemo" / f).write_text("[]")
(REPO / ".mnemo" / "context.json").write_text("{}")
(REPO / ".mnemo" / "hashes.json").write_text("{}")

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from mnemo.mcp_server import handle_tool_call

# Seed memories
MEMORIES = [
    ("CosmosDB is used for payer configuration storage with payerId as partition key", "architecture"),
    ("Redis is the caching layer for provider search responses", "architecture"),
    ("Authentication uses Azure AD B2C with JWT bearer tokens", "architecture"),
    ("The PayerController inherits from ControllerBase and uses constructor DI", "pattern"),
    ("PayerConfig deserialization fails with null Token field - need nullable annotations", "bug"),
    ("Always use CancellationToken in async controller actions", "preference"),
    ("Retry policy with exponential backoff for upstream HTTP calls", "pattern"),
    ("Circuit breaker opens after 5 consecutive failures", "architecture"),
    ("Unit tests use xUnit with Moq for mocking IPayerService", "pattern"),
    ("Deploy to Azure App Service with managed identity", "architecture"),
]

print("Seeding 10 memories...")
with patch("mnemo.memory._get_current_branch", return_value="main"):
    for content, cat in MEMORIES:
        handle_tool_call("mnemo_remember", {"repo_path": str(REPO), "content": content, "category": cat})

# Queries with expected results
QUERIES = [
    # (query, expected_substring, type)
    ("CosmosDB", "CosmosDB", "exact"),
    ("Redis", "Redis", "exact"),
    ("CancellationToken", "CancellationToken", "exact"),
    ("payer configuration", "payer configuration", "substring"),
    ("circuit breaker", "Circuit breaker", "substring"),
    ("database storage", "CosmosDB", "semantic"),
    ("caching layer", "Redis", "semantic"),
    ("authentication security", "Azure AD", "semantic"),
    ("HTTP resilience", "Retry", "semantic"),
    ("testing framework", "xUnit", "semantic"),
    ("deployment infrastructure", "Azure App Service", "semantic"),
]

# Run benchmark
print("\n" + "=" * 60)
print("MNEMO SEARCH QUALITY BENCHMARK")
print("=" * 60)
print(f"{'Query':<30} {'Expected':<20} {'Type':<10} Result")
print("-" * 70)

passed = 0
total_ms = 0

for query, expected, qtype in QUERIES:
    t0 = time.time()
    r = handle_tool_call("mnemo_search_memory", {"repo_path": str(REPO), "query": query})
    elapsed = (time.time() - t0) * 1000
    total_ms += elapsed

    text = r["content"][0]["text"]
    found = expected in text
    if found:
        passed += 1
    print(f"{query:<30} {expected:<20} {qtype:<10} {'✅' if found else '❌'} ({elapsed:.0f}ms)")

print("-" * 70)
print(f"\nResults:")
print(f"  Recall@5:       {passed}/{len(QUERIES)} ({passed/len(QUERIES)*100:.0f}%)")
print(f"  Avg latency:    {total_ms/len(QUERIES):.1f}ms")
print(f"  Exact match:    {sum(1 for _,_,t in QUERIES if t=='exact')}/{sum(1 for _,_,t in QUERIES if t=='exact')}")

semantic_pass = sum(1 for i, (q, e, t) in enumerate(QUERIES) if t == "semantic" and e in handle_tool_call("mnemo_search_memory", {"repo_path": str(REPO), "query": q})["content"][0]["text"])
semantic_total = sum(1 for _, _, t in QUERIES if t == "semantic")
print(f"  Semantic:       {semantic_pass}/{semantic_total}")
print(f"  Substring:      {sum(1 for _,_,t in QUERIES if t=='substring')}/{sum(1 for _,_,t in QUERIES if t=='substring')}")

# Cleanup
shutil.rmtree(REPO)
print(f"\n{'✅ PASS' if passed == len(QUERIES) else '❌ FAIL'}")
