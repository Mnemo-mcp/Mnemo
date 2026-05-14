"""Secret stripping for memory content."""

from __future__ import annotations
import re

_PATTERNS = [
    re.compile(r'AKIA[0-9A-Z]{16}'),
    re.compile(r'sk-[a-zA-Z0-9_-]{20,}'),
    re.compile(r'sk_live_[a-zA-Z0-9]{20,}'),
    re.compile(r'ghp_[a-zA-Z0-9]{10,}'),
    re.compile(r'gho_[a-zA-Z0-9]{10,}'),
    re.compile(r'ghs_[a-zA-Z0-9]{10,}'),
    re.compile(r'ghr_[a-zA-Z0-9]{10,}'),
    re.compile(r'npm_[a-zA-Z0-9]{10,}'),
    re.compile(r'eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}(?:\.[a-zA-Z0-9_-]+)?'),
    re.compile(r'Bearer\s+[a-zA-Z0-9_\-.]{20,}'),
    re.compile(r'xoxb-[a-zA-Z0-9\-]+'),
    re.compile(r'xoxp-[a-zA-Z0-9\-]+'),
    re.compile(r'AIza[a-zA-Z0-9_-]{35}'),
    re.compile(r'glpat-[a-zA-Z0-9_-]{20,}'),
    re.compile(r'dop_v1_[a-f0-9]{64}'),
    re.compile(r'<private>.*?</private>', re.DOTALL),
]


def strip_secrets(content: str) -> tuple[str, int]:
    """Strip secrets from content. Returns (cleaned, count_redacted)."""

    count = 0
    for pat in _PATTERNS:
        matches = pat.findall(content)
        count += len(matches)
        content = pat.sub('[REDACTED]', content)
    return content, count
