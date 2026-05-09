"""Roslyn analyzer bridge — uses .NET SDK when available for richer C# analysis."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

_ANALYZER_DIR = Path(__file__).parent.parent.parent / "analyzers" / "roslyn"


def dotnet_available() -> bool:
    """Check if .NET SDK is installed."""
    return shutil.which("dotnet") is not None


def _find_solution_or_project(repo_root: Path) -> Path | None:
    """Find .sln or .csproj in the repo."""
    slns = list(repo_root.glob("*.sln"))
    if slns:
        return slns[0]
    csprojs = list(repo_root.rglob("*.csproj"))
    if csprojs:
        return repo_root
    return None


def roslyn_available(repo_root: Path) -> bool:
    """Check if Roslyn analysis is possible for this repo."""
    if not dotnet_available():
        return False
    return _find_solution_or_project(repo_root) is not None


def run_roslyn_analyzer(repo_root: Path) -> list[dict[str, Any]] | None:
    """Run the Roslyn analyzer and return parsed results."""
    if not dotnet_available():
        return None

    target = _find_solution_or_project(repo_root)
    if target is None:
        return None

    try:
        result = subprocess.run(
            ["dotnet", "run", "--project", str(_ANALYZER_DIR), "--", str(target)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(repo_root),
        )
        if result.returncode != 0:
            return None
        # stdout may have warnings before JSON — find the JSON array
        stdout = result.stdout.strip()
        json_start = stdout.find("[")
        if json_start == -1:
            return None
        return json.loads(stdout[json_start:])
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return None


def roslyn_to_mnemo_format(roslyn_results: list[dict[str, Any]], repo_root: Path) -> dict[str, dict[str, Any]]:
    """Convert Roslyn JSON output to the same format tree-sitter extractors return.

    Returns: {relative_file_path: {"imports": [...], "classes": [...], "functions": [...]}}
    """
    output: dict[str, dict[str, Any]] = {}

    for file_entry in roslyn_results:
        filepath = file_entry.get("file", "")
        if not filepath:
            continue

        # Make path relative to repo root
        try:
            rel = str(Path(filepath).relative_to(repo_root))
        except ValueError:
            rel = filepath

        info: dict[str, Any] = {}

        imports = file_entry.get("imports", [])
        if imports:
            info["imports"] = imports

        classes = file_entry.get("classes", [])
        if classes:
            info["classes"] = []
            for cls in classes:
                entry: dict[str, Any] = {"name": cls["name"]}
                if cls.get("implements"):
                    entry["implements"] = cls["implements"]
                if cls.get("methods"):
                    entry["methods"] = cls["methods"]
                info["classes"].append(entry)

        functions = file_entry.get("functions", [])
        if functions:
            info["functions"] = functions

        if info:
            output[rel] = info

    return output
