"""MNO-033: Performance benchmarks for recall and search latency."""

import json
import time
from pathlib import Path
from unittest.mock import patch


def setup_repo(tmp_path: Path) -> Path:
    d = tmp_path / ".mnemo"
    d.mkdir(parents=True)
    for f in ("decisions.json", "plans.json", "tasks.json"):
        (d / f).write_text("[]")
    (d / "context.json").write_text("{}")
    (d / "hashes.json").write_text("{}")
    (d / "tree.md").write_text("# Tree\n- src/\n  - main.py\n")
    entries = []
    now = time.time()
    for i in range(100):
        entries.append({
            "id": i + 1,
            "timestamp": now - i * 3600,
            "category": "general",
            "content": f"Memory entry about topic {i} with details on feature {i % 10}",
            "access_count": i % 5,
            "confidence": 0.8,
            "recall_count": 0,
            "last_recalled": None,
            "tier": "session",
            "importance": 2,
        })
    (d / "memory.json").write_text(json.dumps(entries))
    return tmp_path


def benchmark_recall(repo: Path) -> float:
    from mnemo.memory.search import recall
    with patch("mnemo.repo_map.has_changes", return_value=False):
        start = time.perf_counter()
        recall(repo, tier="standard")
        return (time.perf_counter() - start) * 1000


def benchmark_search(repo: Path) -> float:
    from mnemo.memory import search_memory
    start = time.perf_counter()
    search_memory(repo, "topic feature details")
    return (time.perf_counter() - start) * 1000


def main():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        repo = setup_repo(Path(tmp))

        recall_times = [benchmark_recall(repo) for _ in range(5)]
        search_times = [benchmark_search(repo) for _ in range(5)]

    avg_recall = sum(recall_times) / len(recall_times)
    avg_search = sum(search_times) / len(search_times)

    print(f"{'Benchmark':<25} {'Avg (ms)':<12} {'Target':<12} {'Status'}")
    print("-" * 60)
    print(f"{'Recall (standard)':<25} {avg_recall:<12.1f} {'<500ms':<12} {'✓ PASS' if avg_recall < 500 else '✗ FAIL'}")
    print(f"{'Search (100 memories)':<25} {avg_search:<12.1f} {'<200ms':<12} {'✓ PASS' if avg_search < 200 else '✗ FAIL'}")


if __name__ == "__main__":
    main()
