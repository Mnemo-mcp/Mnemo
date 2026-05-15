"""Repo Identity Model — auto-inferred conventions, patterns, and style profile."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ..config import mnemo_path
from ..intelligence import classify_architecture, detect_dependencies, detect_patterns


IDENTITY_FILE = "repo_identity.json"


def generate_identity(repo_root: Path) -> dict[str, Any]:
    """Generate a repo identity profile from code analysis."""
    patterns = detect_patterns(repo_root)
    architectures = classify_architecture(repo_root)
    deps = detect_dependencies(repo_root)

    # Extract top dependencies (most common across projects)
    all_deps: list[str] = []
    for pkgs in deps.values():
        all_deps.extend(pkg.split()[0] for pkg in pkgs)

    # Detect language distribution using os.walk (single pass, not 20 rglobs)
    import os
    from ..config import SUPPORTED_EXTENSIONS, IGNORE_DIRS
    lang_counts: dict[str, int] = {}
    ext_to_lang = {ext: lang for ext, lang in SUPPORTED_EXTENSIONS.items()}
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for filename in filenames:
            for ext, lang in ext_to_lang.items():
                if filename.endswith(ext):
                    lang_counts[lang] = lang_counts.get(lang, 0) + 1
                    break

    # Sort by count
    primary_languages = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    identity: dict[str, Any] = {
        "generated_at": time.time(),
        "languages": [lang for lang, _ in primary_languages],
        "patterns": patterns[:10],
        "architecture_styles": [
            {"name": a["name"], "confidence": a["confidence"]}
            for a in architectures[:3]
        ],
        "key_dependencies": list(set(all_deps))[:20],
        "conventions": _infer_conventions(repo_root, patterns),
    }
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
