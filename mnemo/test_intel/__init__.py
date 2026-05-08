"""Test Intelligence — map tests to source code, know what to run/update."""

from __future__ import annotations

import re
from pathlib import Path

from ..config import IGNORE_DIRS


def _should_ignore(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)


def build_test_map(repo_root: Path) -> dict[str, list[str]]:
    """Map source files to their test files based on naming conventions and imports."""
    test_files: list[Path] = []
    source_files: list[Path] = []

    for cs_file in repo_root.rglob("*.cs"):
        if _should_ignore(cs_file):
            continue
        rel = str(cs_file.relative_to(repo_root))
        if "Test" in rel:
            test_files.append(cs_file)
        else:
            source_files.append(cs_file)

    # Map: source_file → [test_files]
    test_map: dict[str, list[str]] = {}

    for source in source_files:
        source_name = source.stem  # e.g. "AuthorizationService"
        source_rel = str(source.relative_to(repo_root))
        matching_tests = []

        for test in test_files:
            test_name = test.stem
            # Convention: FooTests.cs tests Foo.cs
            if source_name in test_name:
                matching_tests.append(str(test.relative_to(repo_root)))
                continue

            # Check if test imports/uses the source class
            try:
                content = test.read_text(errors="replace")
                if source_name in content:
                    matching_tests.append(str(test.relative_to(repo_root)))
            except (OSError, PermissionError):
                continue

        if matching_tests:
            test_map[source_rel] = matching_tests

    return test_map


def get_tests_for_file(repo_root: Path, filepath: str) -> str:
    """Get all tests that cover a specific file."""
    test_map = build_test_map(repo_root)
    query = filepath.lower()

    matches = []
    for source, tests in test_map.items():
        if query in source.lower():
            matches.append((source, tests))

    if not matches:
        return f"No tests found for '{filepath}'."

    lines = [f"# Tests for '{filepath}'\n"]
    for source, tests in matches:
        lines.append(f"## {source}")
        for t in tests:
            lines.append(f"- {t}")
        lines.append("")
    return "\n".join(lines)


def get_coverage_summary(repo_root: Path) -> str:
    """Get a summary of test coverage by service."""
    test_map = build_test_map(repo_root)

    # Group by service
    by_service: dict[str, dict] = {}
    for source, tests in test_map.items():
        parts = source.split("/")
        svc = parts[0] if len(parts) > 1 else "root"
        if svc not in by_service:
            by_service[svc] = {"covered": 0, "tests": 0}
        by_service[svc]["covered"] += 1
        by_service[svc]["tests"] += len(tests)

    # Count total source files per service
    total_by_service: dict[str, int] = {}
    for cs_file in repo_root.rglob("*.cs"):
        if _should_ignore(cs_file) or "Test" in str(cs_file):
            continue
        parts = cs_file.relative_to(repo_root).parts
        svc = parts[0] if len(parts) > 1 else "root"
        total_by_service[svc] = total_by_service.get(svc, 0) + 1

    lines = ["# Test Coverage Summary\n"]
    for svc in sorted(set(list(by_service.keys()) + list(total_by_service.keys()))):
        total = total_by_service.get(svc, 0)
        covered = by_service.get(svc, {}).get("covered", 0)
        tests = by_service.get(svc, {}).get("tests", 0)
        pct = f"{covered/total*100:.0f}%" if total > 0 else "0%"
        lines.append(f"- **{svc}**: {covered}/{total} files covered ({pct}), {tests} test files")

    return "\n".join(lines)
