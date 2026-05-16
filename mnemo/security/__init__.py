"""Security pattern memory — uses engine/ graph for file discovery, regex for detection."""

from __future__ import annotations

import re
import time
from pathlib import Path

from ..config import mnemo_path

STORAGE_FILE = "security_patterns.json"

BUILTIN_PATTERNS = [
    {"name": "hardcoded_secret", "regex": r"(password|secret|api_key|token)\s*=\s*[\"'][^\"']{8,}", "severity": "high", "description": "Hardcoded secret or credential"},
    {"name": "sql_injection", "regex": r"(execute|query)\s*\(\s*f[\"']|\.format\(.*\)|%\s*\(", "severity": "high", "description": "Potential SQL injection via string formatting"},
    {"name": "eval_usage", "regex": r"\beval\s*\(", "severity": "medium", "description": "Use of eval() - potential code injection"},
    {"name": "shell_injection", "regex": r"os\.system\(|subprocess\.\w+\(.*shell\s*=\s*True", "severity": "high", "description": "Potential shell injection"},
    {"name": "insecure_http", "regex": r"http://(?!localhost|127\.0\.0\.1)", "severity": "low", "description": "Insecure HTTP URL (not HTTPS)"},
]


def _load_patterns(repo_root: Path) -> list[dict]:
    import json
    path = mnemo_path(repo_root) / STORAGE_FILE
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_patterns(repo_root: Path, patterns: list[dict]) -> None:
    import json
    path = mnemo_path(repo_root) / STORAGE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(patterns, indent=2) + "\n", encoding="utf-8")


def add_security_pattern(repo_root: Path, name: str, regex: str, severity: str = "medium", description: str = "") -> dict:
    """Add a custom security pattern."""
    patterns = _load_patterns(repo_root)
    next_id = max((p.get("id", 0) for p in patterns), default=0) + 1
    entry = {"id": next_id, "timestamp": time.time(), "name": name, "regex": regex, "severity": severity, "description": description or name}
    patterns.append(entry)
    _save_patterns(repo_root, patterns)
    return entry


def check_security(repo_root: Path, file_path: str = "") -> str:
    """Scan for security issues. Uses engine graph for file list, regex for detection."""
    patterns = BUILTIN_PATTERNS + _load_patterns(repo_root)
    findings: list[dict] = []

    # Get file list from engine graph
    files: list[str] = []
    if file_path:
        files = [file_path]
    else:
        try:
            from ..engine.db import open_db, get_db_path
            if get_db_path(repo_root).exists():
                _, conn = open_db(repo_root)
                result = conn.execute("MATCH (f:File) WHERE NOT f.path CONTAINS 'test' RETURN f.path")
                while result.has_next():
                    files.append(result.get_next()[0])
        except Exception:
            pass
        if not files:
            # Fallback: walk filesystem
            from ..config import SUPPORTED_EXTENSIONS, should_ignore
            for ext in SUPPORTED_EXTENSIONS:
                for fp in repo_root.rglob(f"*{ext}"):
                    if not should_ignore(fp) and fp.stat().st_size <= 200_000:
                        files.append(str(fp.relative_to(repo_root)))

    for rel in files:
        fp = repo_root / rel
        if not fp.exists():
            continue
        try:
            content = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        for pattern in patterns:
            try:
                matches = list(re.finditer(pattern["regex"], content, re.IGNORECASE))
            except re.error:
                continue
            for match in matches:
                line_num = content[:match.start()].count("\n") + 1
                findings.append({
                    "file": rel, "line": line_num,
                    "pattern": pattern["name"],
                    "severity": pattern.get("severity", "medium"),
                    "description": pattern.get("description", ""),
                    "match": match.group()[:80],
                })

    if not findings:
        return f"No security issues found in {'`' + file_path + '`' if file_path else 'codebase'}."

    lines = [f"# Security Scan ({len(findings)} findings)\n"]
    by_severity = {"high": [], "medium": [], "low": []}
    for f in findings:
        by_severity.setdefault(f["severity"], []).append(f)

    for sev in ("high", "medium", "low"):
        items = by_severity.get(sev, [])
        if not items:
            continue
        lines.append(f"## {sev.upper()} ({len(items)})\n")
        for item in items[:20]:
            lines.append(f"- **{item['file']}:{item['line']}** — {item['description']}")
            lines.append(f"  `{item['match']}`")
        lines.append("")

    return "\n".join(lines)
