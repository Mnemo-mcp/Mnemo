"""Repo Identity Model — auto-inferred conventions, patterns, and style profile."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import mnemo_path


IDENTITY_FILE = "repo_identity.json"


def generate_identity(repo_root: Path) -> dict[str, Any]:
    """Generate a repo identity profile from engine graph."""
    identity: dict[str, Any] = {}
    try:
        from ..engine.db import open_db, get_db_path
        if not get_db_path(repo_root).exists():
            return identity
        _, conn = open_db(repo_root)
        # Languages
        r = conn.execute("MATCH (f:File) RETURN f.language, count(f) ORDER BY count(f) DESC")
        langs = []
        while r.has_next():
            row = r.get_next()
            langs.append(f"{row[0]} ({row[1]})")
        identity["languages"] = langs
        # Projects
        r = conn.execute("MATCH (p:Project) RETURN p.name, p.language")
        projects = []
        while r.has_next():
            row = r.get_next()
            projects.append({"name": row[0], "language": row[1]})
        identity["projects"] = projects
        # Stats
        r = conn.execute("MATCH (n) RETURN count(n)")
        identity["total_nodes"] = r.get_next()[0]
    except Exception:
        pass
    return identity


def _infer_conventions(repo_root: Path, patterns: list[str]) -> list[str]:
    """Infer coding conventions from detected patterns and file structure."""
    conventions: list[str] = []

    # Check for linter configs
    linter_files = {
        ".eslintrc": "ESLint",
        ".eslintrc.json": "ESLint",
        "ruff.toml": "Ruff",
        ".flake8": "Flake8",
        "pyproject.toml": "pyproject.toml config",
        ".editorconfig": "EditorConfig",
        ".prettierrc": "Prettier",
    }
    for filename, tool in linter_files.items():
        if (repo_root / filename).exists():
            conventions.append(f"Uses {tool}")

    # Check test structure
    test_dirs = [d for d in repo_root.iterdir() if d.is_dir() and "test" in d.name.lower()]
    if test_dirs:
        conventions.append(f"Tests in: {', '.join(d.name for d in test_dirs[:3])}")

    # Infer from patterns
    for p in patterns:
        if "DI" in p or "dependency injection" in p.lower():
            conventions.append("Dependency injection")
        if "interface" in p.lower():
            conventions.append("Interface-first design")

    return conventions[:10]


def save_identity(repo_root: Path) -> str:
    """Generate and save repo identity to .mnemo/repo_identity.json."""
    identity = generate_identity(repo_root)
    path = mnemo_path(repo_root) / IDENTITY_FILE
    path.write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
    return f"Repo identity saved: {len(identity['languages'])} languages, {len(identity['patterns'])} patterns, {len(identity['conventions'])} conventions"


def load_identity(repo_root: Path) -> dict[str, Any] | None:
    """Load saved repo identity."""
    path = mnemo_path(repo_root) / IDENTITY_FILE
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def format_identity(repo_root: Path) -> str:
    """Format repo identity for inclusion in recall."""
    identity = load_identity(repo_root)
    if not identity:
        return ""

    lines = ["# Repo Identity"]
    if identity.get("languages"):
        lines.append(f"- **Languages**: {', '.join(identity['languages'])}")
    if identity.get("architecture_styles"):
        styles = [f"{a['name']} ({a['confidence']})" for a in identity["architecture_styles"]]
        lines.append(f"- **Architecture**: {', '.join(styles)}")
    if identity.get("patterns"):
        lines.append(f"- **Patterns**: {'; '.join(identity['patterns'][:5])}")
    if identity.get("conventions"):
        lines.append(f"- **Conventions**: {'; '.join(identity['conventions'][:5])}")
    lines.append("")
    return "\n".join(lines)
