"""Content-addressed parse cache — SHA-256 hash → ParseResult."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .pipeline import ParseResult


def _cache_path(repo_root: Path) -> Path:
    return repo_root / ".mnemo" / "parse-cache.json"


def load_cache(repo_root: Path) -> dict[str, ParseResult]:
    """Load parse cache from disk."""
    path = _cache_path(repo_root)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {k: _from_dict(v) for k, v in data.items()}
    except (json.JSONDecodeError, OSError, KeyError):
        return {}


def save_cache(repo_root: Path, cache: dict[str, ParseResult]) -> None:
    """Save parse cache to disk."""
    path = _cache_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {k: _to_dict(v) for k, v in cache.items()}
    path.write_text(json.dumps(data), encoding="utf-8")


def get_cached(cache: dict[str, ParseResult], file_hash: str) -> ParseResult | None:
    """Get a cached parse result by file content hash."""
    return cache.get(file_hash)


def _to_dict(r: ParseResult) -> dict[str, Any]:
    return {
        "path": r.path,
        "language": r.language,
        "classes": r.classes,
        "functions": r.functions,
        "imports": r.imports,
    }


def _from_dict(d: dict[str, Any]) -> ParseResult:
    return ParseResult(
        path=d["path"],
        language=d["language"],
        classes=d.get("classes", []),
        functions=d.get("functions", []),
        imports=d.get("imports", []),
    )
