"""Mnemo configuration and constants."""

from __future__ import annotations

from pathlib import Path

MNEMO_DIR = ".mnemo"
MEMORY_FILE = "memory.json"
REPO_MAP_FILE = "repo_map.json"
DECISIONS_FILE = "decisions.json"
CONTEXT_FILE = "context.json"
MNEMOIGNORE_FILE = ".mnemoignore"

MAX_FILE_SIZE = 200_000  # 200KB — skip files larger than this during indexing

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


def load_mnemoignore(repo_root: Path) -> set[str]:
    """Read user-supplied directory names from <repo>/.mnemoignore.

    Each non-blank, non-comment line is treated as a directory basename to
    ignore during indexing. Patterns match the same way as IGNORE_DIRS:
    by exact basename, anywhere in the tree. This intentionally mirrors the
    existing hardcoded set so the file is easy to reason about; glob /
    .gitignore semantics can be a future enhancement.

    Returns an empty set if the file does not exist or cannot be read.
    """
    path = repo_root / MNEMOIGNORE_FILE
    if not path.is_file():
        return set()
    extras: set[str] = set()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Tolerate trailing slashes (e.g. "data/") and quotes.
        line = line.rstrip("/").strip('"').strip("'")
        if line:
            extras.add(line)
    return extras


def ignore_dirs_for(repo_root: Path) -> set[str]:
    """Return the effective ignore set for a repo: defaults plus .mnemoignore."""
    return IGNORE_DIRS | load_mnemoignore(repo_root)


def should_ignore(path: Path, repo_root: Path | None = None) -> bool:
    """Check if a path should be ignored based on directory name.

    Uses IGNORE_DIRS + .mnemoignore (if repo_root provided).
    """
    dirs = ignore_dirs_for(repo_root) if repo_root else IGNORE_DIRS
    return any(part in dirs for part in path.parts)
