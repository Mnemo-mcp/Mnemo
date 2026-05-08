"""Mnemo configuration and constants."""

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
    ".go": "go",
    ".cs": "csharp",
}

IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".mnemo", ".tox", ".mypy_cache", "egg-info",
    "bin", "obj", "packages", ".vs",
    "wwwroot", "publish", "artifacts", "TestResults",
}


def mnemo_path(repo_root: Path) -> Path:
    return repo_root / MNEMO_DIR
