"""Convention enforcer — detects and validates project conventions (MNO-609)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..config import SUPPORTED_EXTENSIONS, mnemo_path, should_ignore
from ..repo_map import _extract_file, MAX_FILE_SIZE


CONVENTIONS_FILE = "conventions.json"

# Built-in convention detectors
_NAMING_PATTERNS = {
    "python": {
        "class": re.compile(r"^[A-Z][a-zA-Z0-9]+$"),  # PascalCase
        "function": re.compile(r"^[a-z_][a-z0-9_]*$"),  # snake_case
        "constant": re.compile(r"^[A-Z][A-Z0-9_]+$"),  # UPPER_SNAKE
    },
    "typescript": {
        "class": re.compile(r"^[A-Z][a-zA-Z0-9]+$"),  # PascalCase
        "function": re.compile(r"^[a-z][a-zA-Z0-9]*$"),  # camelCase
        "interface": re.compile(r"^I?[A-Z][a-zA-Z0-9]+$"),  # IFoo or Foo
    },
    "csharp": {
        "class": re.compile(r"^[A-Z][a-zA-Z0-9]+$"),  # PascalCase
        "function": re.compile(r"^[A-Z][a-zA-Z0-9]+$"),  # PascalCase methods
        "interface": re.compile(r"^I[A-Z][a-zA-Z0-9]+$"),  # IFoo
    },
}

# Language mapping from extensions
_EXT_TO_LANG = {
    ".py": "python", ".js": "typescript", ".ts": "typescript",
    ".jsx": "typescript", ".tsx": "typescript",
    ".cs": "csharp", ".java": "csharp", ".go": "python",
}


def _load_conventions(repo_root: Path) -> dict[str, Any]:
    """Load stored conventions from .mnemo/conventions.json."""
    import json
    path = mnemo_path(repo_root) / CONVENTIONS_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_conventions(repo_root: Path, conventions: dict[str, Any]) -> None:
    """Save conventions to .mnemo/conventions.json."""
    import json
    path = mnemo_path(repo_root) / CONVENTIONS_FILE
    path.write_text(json.dumps(conventions, indent=2), encoding="utf-8")


def detect_conventions(repo_root: Path) -> dict[str, Any]:
    """Auto-detect project conventions by analyzing codebase patterns."""
    conventions: dict[str, Any] = {"naming": {}, "structure": {}, "patterns": []}

    # Analyze file structure
    top_dirs = sorted(
        d.name for d in repo_root.iterdir()
        if d.is_dir() and not d.name.startswith(".") and d.name not in ("node_modules", "__pycache__", "dist", "build")
    )
    conventions["structure"]["top_level_dirs"] = top_dirs

    # Detect naming conventions by sampling symbols
    naming_stats: dict[str, dict[str, dict[str, int]]] = {}  # lang -> symbol_type -> {pattern: count}

    sample_count = 0
    for ext, language in SUPPORTED_EXTENSIONS.items():
        lang_key = _EXT_TO_LANG.get(ext)
        if not lang_key or lang_key not in _NAMING_PATTERNS:
            continue

        for filepath in repo_root.rglob(f"*{ext}"):
            if should_ignore(filepath) or filepath.stat().st_size > MAX_FILE_SIZE:
                continue
            sample_count += 1
            if sample_count > 100:
                break

            try:
                source = filepath.read_bytes()
            except (OSError, PermissionError):
                continue

            info = _extract_file(source, language)
            if not info:
                continue

            naming_stats.setdefault(lang_key, {})

            # Check classes
            for cls in info.get("classes", []):
                name = cls.get("name", "") if isinstance(cls, dict) else cls
                if isinstance(cls, dict):
                    name = cls.get("name", "")
                naming_stats[lang_key].setdefault("class", {"conforming": 0, "total": 0})
                naming_stats[lang_key]["class"]["total"] += 1
                if _NAMING_PATTERNS[lang_key]["class"].match(name):
                    naming_stats[lang_key]["class"]["conforming"] += 1

            # Check functions
            for func in info.get("functions", []):
                # Extract function name from signature
                name = func.split("(")[0].strip().split()[-1] if "(" in func else func
                name = name.lstrip("*&")
                if not name or name.startswith("@"):
                    continue
                naming_stats[lang_key].setdefault("function", {"conforming": 0, "total": 0})
                naming_stats[lang_key]["function"]["total"] += 1
                if _NAMING_PATTERNS[lang_key]["function"].match(name):
                    naming_stats[lang_key]["function"]["conforming"] += 1

    # Summarize naming conventions
    for lang, types in naming_stats.items():
        conventions["naming"][lang] = {}
        for sym_type, counts in types.items():
            total = counts["total"]
            if total > 0:
                pct = counts["conforming"] / total
                conventions["naming"][lang][sym_type] = {
                    "conformance": round(pct, 2),
                    "expected_pattern": _NAMING_PATTERNS[lang][sym_type].pattern,
                }

    # Detect common file patterns
    patterns = []
    test_dirs = [d for d in ("tests", "test", "spec", "__tests__") if (repo_root / d).exists()]
    if test_dirs:
        patterns.append(f"Tests in: {', '.join(test_dirs)}")

    if (repo_root / "src").exists():
        patterns.append("Source in src/ directory")

    config_files = [f.name for f in repo_root.iterdir() if f.is_file() and f.suffix in (".toml", ".yaml", ".yml", ".json") and "config" in f.name.lower() or f.name in ("pyproject.toml", "package.json", "tsconfig.json")]
    if config_files:
        patterns.append(f"Config files: {', '.join(config_files[:5])}")

    conventions["patterns"] = patterns

    _save_conventions(repo_root, conventions)
    return conventions


def check_conventions(repo_root: Path, file: str = "") -> str:
    """Check code against detected conventions. Optionally scope to a single file."""
    conventions = _load_conventions(repo_root)
    if not conventions:
        conventions = detect_conventions(repo_root)

    violations: list[dict[str, str]] = []
    files_checked = 0

    for ext, language in SUPPORTED_EXTENSIONS.items():
        lang_key = _EXT_TO_LANG.get(ext)
        if not lang_key or lang_key not in _NAMING_PATTERNS:
            continue

        lang_conventions = conventions.get("naming", {}).get(lang_key, {})
        if not lang_conventions:
            continue

        for filepath in repo_root.rglob(f"*{ext}"):
            if should_ignore(filepath) or filepath.stat().st_size > MAX_FILE_SIZE:
                continue
            rel = str(filepath.relative_to(repo_root))
            if file and file not in rel:
                continue

            try:
                source = filepath.read_bytes()
            except (OSError, PermissionError):
                continue

            info = _extract_file(source, language)
            if not info:
                continue
            files_checked += 1

            # Check class naming
            if lang_conventions.get("class", {}).get("conformance", 1.0) >= 0.8:
                pattern = _NAMING_PATTERNS[lang_key]["class"]
                for cls in info.get("classes", []):
                    name = cls.get("name", "") if isinstance(cls, dict) else cls
                    if isinstance(cls, dict):
                        name = cls.get("name", "")
                    if name and not pattern.match(name):
                        violations.append({
                            "file": rel, "symbol": name, "type": "class",
                            "issue": f"Class `{name}` doesn't match convention ({pattern.pattern})",
                        })

            # Check function naming
            if lang_conventions.get("function", {}).get("conformance", 1.0) >= 0.8:
                pattern = _NAMING_PATTERNS[lang_key]["function"]
                for func in info.get("functions", []):
                    name = func.split("(")[0].strip().split()[-1] if "(" in func else func
                    name = name.lstrip("*&")
                    if not name or name.startswith("@") or name.startswith("_"):
                        continue
                    if not pattern.match(name):
                        violations.append({
                            "file": rel, "symbol": name, "type": "function",
                            "issue": f"Function `{name}` doesn't match convention ({pattern.pattern})",
                        })

    # Format output
    if not violations:
        return f"✅ No convention violations found ({files_checked} files checked)."

    lines = [f"# Convention Violations ({len(violations)} found, {files_checked} files checked)\n"]
    by_file: dict[str, list[dict[str, str]]] = {}
    for v in violations:
        by_file.setdefault(v["file"], []).append(v)

    for fpath, file_violations in sorted(by_file.items()):
        lines.append(f"## {fpath}")
        for v in file_violations:
            lines.append(f"- ⚠️ {v['issue']}")
        lines.append("")

    return "\n".join(lines)
