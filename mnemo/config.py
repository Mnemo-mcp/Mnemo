"""Mnemo configuration and constants."""

from __future__ import annotations

from pathlib import Path

MNEMO_DIR = ".mnemo"
MEMORY_FILE = "memory.json"
REPO_MAP_FILE = "repo_map.json"
DECISIONS_FILE = "decisions.json"
CONTEXT_FILE = "context.json"

SUPPORTED_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".vue": "javascript",
    ".go": "go",
    ".cs": "csharp",
    ".java": "java",
    ".rs": "rust",
    # Optional (available with pip install mnemo[all-languages])
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".swift": "swift",
    ".scala": "scala",
    ".sc": "scala",
}

IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".mnemo", ".tox", ".mypy_cache", "egg-info",
    "bin", "obj", "packages", ".vs",
    "wwwroot", "publish", "artifacts", "TestResults",
    "target", "vendor", ".gradle", ".idea", ".next", "_next", "out",
    ".competitor_analysis",
}


def mnemo_path(repo_root: Path) -> Path:
    return repo_root / MNEMO_DIR


def should_ignore(path: Path) -> bool:
    """Check if a path should be ignored based on directory name."""

    return any(part in IGNORE_DIRS for part in path.parts)
