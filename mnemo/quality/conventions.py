"""Convention enforcer — checks naming conventions via engine/ graph queries."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..config import mnemo_path

CONVENTIONS_FILE = "conventions.json"

_NAMING_PATTERNS = {
    "python": {"class": re.compile(r"^[A-Z][a-zA-Z0-9]+$"), "function": re.compile(r"^[a-z_][a-z0-9_]*$")},
    "typescript": {"class": re.compile(r"^[A-Z][a-zA-Z0-9]+$"), "function": re.compile(r"^[a-z][a-zA-Z0-9]*$")},
    "javascript": {"class": re.compile(r"^[A-Z][a-zA-Z0-9]+$"), "function": re.compile(r"^[a-z][a-zA-Z0-9]*$")},
    "csharp": {"class": re.compile(r"^[A-Z][a-zA-Z0-9]+$"), "function": re.compile(r"^[A-Z][a-zA-Z0-9]+$")},
}

_LANG_MAP = {"python": "python", "javascript": "typescript", "typescript": "typescript", "csharp": "csharp"}


def _load_conventions(repo_root: Path) -> dict[str, Any]:
    import json
    path = mnemo_path(repo_root) / CONVENTIONS_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_conventions(repo_root: Path, conventions: dict[str, Any]) -> None:
    import json
    path = mnemo_path(repo_root) / CONVENTIONS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(conventions, indent=2), encoding="utf-8")


def detect_conventions(repo_root: Path) -> dict[str, Any]:
    """Auto-detect naming conventions from graph symbols."""
    from ..engine.db import open_db, get_db_path

    conventions: dict[str, Any] = {"naming": {}, "structure": {}, "patterns": []}

    if not get_db_path(repo_root).exists():
        return conventions

    _, conn = open_db(repo_root)

    # Analyze class naming by language
    result = conn.execute("MATCH (f:File)-[:FILE_DEFINES_CLASS]->(c:Class) RETURN f.language, c.name")
    lang_stats: dict[str, dict[str, dict[str, int]]] = {}
    while result.has_next():
        row = result.get_next()
        lang = _LANG_MAP.get(row[0], row[0])
        if lang not in _NAMING_PATTERNS:
            continue
        lang_stats.setdefault(lang, {}).setdefault("class", {"conforming": 0, "total": 0})
        lang_stats[lang]["class"]["total"] += 1
        if _NAMING_PATTERNS[lang]["class"].match(row[1] or ""):
            lang_stats[lang]["class"]["conforming"] += 1

    # Analyze function naming by language
    result = conn.execute("MATCH (f:File)-[:FILE_DEFINES_FUNCTION]->(fn:Function) RETURN f.language, fn.name")
    while result.has_next():
        row = result.get_next()
        lang = _LANG_MAP.get(row[0], row[0])
        if lang not in _NAMING_PATTERNS:
            continue
        name = row[1] or ""
        if name.startswith("_") or name.startswith("@"):
            continue
        lang_stats.setdefault(lang, {}).setdefault("function", {"conforming": 0, "total": 0})
        lang_stats[lang]["function"]["total"] += 1
        if _NAMING_PATTERNS[lang]["function"].match(name):
            lang_stats[lang]["function"]["conforming"] += 1

    for lang, types in lang_stats.items():
        conventions["naming"][lang] = {}
        for sym_type, counts in types.items():
            if counts["total"] > 0:
                conventions["naming"][lang][sym_type] = {
                    "conformance": round(counts["conforming"] / counts["total"], 2),
                    "expected_pattern": _NAMING_PATTERNS[lang][sym_type].pattern,
                }

    # Detect projects
    result = conn.execute("MATCH (p:Project) RETURN p.name, p.language")
    projects = []
    while result.has_next():
        row = result.get_next()
        projects.append(f"{row[0]} ({row[1]})")
    if projects:
        conventions["patterns"].append(f"Projects: {', '.join(projects)}")

    _save_conventions(repo_root, conventions)
    return conventions


def check_conventions(repo_root: Path, file: str = "") -> str:
    """Check naming conventions against graph symbols."""
    from ..engine.db import open_db, get_db_path

    if not get_db_path(repo_root).exists():
        return "No graph database. Run `mnemo init` first."

    conventions = _load_conventions(repo_root)
    if not conventions:
        conventions = detect_conventions(repo_root)

    _, conn = open_db(repo_root)
    violations: list[dict] = []

    # Check class names
    query = "MATCH (f:File)-[:FILE_DEFINES_CLASS]->(c:Class) RETURN f.language, c.name, f.path"
    if file:
        query = f"MATCH (f:File)-[:FILE_DEFINES_CLASS]->(c:Class) WHERE f.path CONTAINS '{file}' RETURN f.language, c.name, f.path"
    result = conn.execute(query)
    while result.has_next():
        row = result.get_next()
        lang = _LANG_MAP.get(row[0], row[0])
        if lang in _NAMING_PATTERNS and row[1]:
            if not _NAMING_PATTERNS[lang]["class"].match(row[1]):
                violations.append({"file": row[2], "symbol": row[1], "issue": f"Class `{row[1]}` doesn't match {_NAMING_PATTERNS[lang]['class'].pattern}"})

    # Check function names
    query = "MATCH (f:File)-[:FILE_DEFINES_FUNCTION]->(fn:Function) RETURN f.language, fn.name, f.path"
    if file:
        query = f"MATCH (f:File)-[:FILE_DEFINES_FUNCTION]->(fn:Function) WHERE f.path CONTAINS '{file}' RETURN f.language, fn.name, f.path"
    result = conn.execute(query)
    while result.has_next():
        row = result.get_next()
        lang = _LANG_MAP.get(row[0], row[0])
        name = row[1] or ""
        if name.startswith("_") or name.startswith("@") or not name:
            continue
        if lang in _NAMING_PATTERNS:
            if not _NAMING_PATTERNS[lang]["function"].match(name):
                violations.append({"file": row[2], "symbol": name, "issue": f"Function `{name}` doesn't match {_NAMING_PATTERNS[lang]['function'].pattern}"})

    if not violations:
        return "✅ No convention violations found."

    lines = [f"# Convention Violations ({len(violations)} found)\n"]
    by_file: dict[str, list[dict]] = {}
    for v in violations:
        by_file.setdefault(v["file"], []).append(v)
    for fpath, fv in sorted(by_file.items()):
        lines.append(f"## {fpath}")
        for v in fv[:10]:
            lines.append(f"- ⚠️ {v['issue']}")
        lines.append("")
    return "\n".join(lines)
