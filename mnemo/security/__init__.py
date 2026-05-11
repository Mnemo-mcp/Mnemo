"""Security pattern memory - store and check unsafe code patterns."""

from __future__ import annotations

import re
import time
from pathlib import Path

from ..config import SUPPORTED_EXTENSIONS, mnemo_path, should_ignore
from ..repo_map import MAX_FILE_SIZE

STORAGE_FILE = "security_patterns.json"

# Built-in patterns
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
    path.write_text(json.dumps(patterns, indent=2) + "\n", encoding="utf-8")


def add_security_pattern(
    repo_root: Path,
    name: str,
    regex: str,
    severity: str = "medium",
    description: str = "",
) -> dict:
    """Add a custom security pattern to watch for."""
    patterns = _load_patterns(repo_root)
    next_id = max((p.get("id", 0) for p in patterns), default=0) + 1
    entry = {
        "id": next_id,
        "timestamp": time.time(),
        "name": name,
        "regex": regex,
        "severity": severity,
        "description": description or name,
    }
    patterns.append(entry)
    _save_patterns(repo_root, patterns)
    return entry


def _strip_comments_and_strings(content: str, file_path: str) -> str:
    """Remove comments and string literals to reduce false positives."""
    ext = file_path.rsplit(".", 1)[-1] if "." in file_path else ""
    lines = content.splitlines()
    cleaned = []
    in_block_comment = False
    in_docstring: str | None = None  # tracks the delimiter (''' or """)

    for line in lines:
        stripped = line.strip()

        # Python docstrings (triple quotes)
        if ext == "py":
            if in_docstring:
                if in_docstring in stripped:
                    in_docstring = None
                cleaned.append("")
                continue
            if stripped.startswith('"""') or stripped.startswith("'''"):
                delimiter = stripped[:3]
                # Single-line docstring: """text""" — check if it closes on same line
                if stripped.count(delimiter) >= 2:
                    cleaned.append("")
                    continue
                in_docstring = delimiter
                cleaned.append("")
                continue

        # C-style block comments
        if ext in ("cs", "js", "ts", "tsx", "jsx", "go"):
            if in_block_comment:
                if "*/" in stripped:
                    in_block_comment = False
                cleaned.append("")
                continue
            if "/*" in stripped:
                in_block_comment = True
                cleaned.append("")
                continue

        # Single-line comments
        if ext == "py" and stripped.startswith("#"):
            cleaned.append("")
            continue
        if ext in ("cs", "js", "ts", "tsx", "jsx", "go") and stripped.startswith("//"):
            cleaned.append("")
            continue

        # Strip inline string literals to avoid false positives on patterns inside strings
        sanitized = re.sub(r'(["\'])(?:(?!\1).)*?\1', '""', line)
        cleaned.append(sanitized)

    return "\n".join(cleaned)


def check_security(repo_root: Path, file_path: str = "") -> str:
    """Scan for security issues using built-in + custom patterns."""
    patterns = BUILTIN_PATTERNS + _load_patterns(repo_root)
    findings: list[dict] = []

    # Determine files to scan
    if file_path:
        files = [repo_root / file_path]
    else:
        files = []
        for ext in SUPPORTED_EXTENSIONS:
            for fp in repo_root.rglob(f"*{ext}"):
                if not should_ignore(fp) and fp.stat().st_size <= MAX_FILE_SIZE:
                    files.append(fp)

    for fp in files:
        if not fp.exists():
            continue
        try:
            raw_content = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(fp.relative_to(repo_root))
        # Strip comments and strings to reduce false positives
        content = _strip_comments_and_strings(raw_content, rel)

        for pattern in patterns:
            try:
                matches = list(re.finditer(pattern["regex"], content, re.IGNORECASE))
            except re.error:
                continue
            for match in matches:
                line_num = content[:match.start()].count("\n") + 1
                findings.append({
                    "file": rel,
                    "line": line_num,
                    "pattern": pattern["name"],
                    "severity": pattern.get("severity", "medium"),
                    "description": pattern.get("description", ""),
                    "match": match.group()[:80],
                })

    if not findings:
        scope = f"`{file_path}`" if file_path else "codebase"
        return f"No security issues found in {scope}."

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
