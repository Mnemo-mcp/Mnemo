"""Shared utilities — small, independent modules used across mnemo packages.

Grouping rationale: Each module is <100 LOC and has no dependencies on other utils.
They're grouped here rather than split into sub-packages because:
- Each is a single-file utility (no internal structure to warrant a package)
- They have zero inter-dependencies
- Flat structure keeps imports simple: `from ..utils import get_logger`

Categories:
- Text processing: stemmer, synonyms
- Safety/compliance: privacy (secret stripping), audit (audit trail)
- Resilience: circuit_breaker, metrics
- Infrastructure: logger, dedup
"""

from __future__ import annotations

import json
from pathlib import Path

from .logger import get_logger
from .privacy import strip_secrets
from .dedup import DedupMap
from .circuit_breaker import CircuitBreaker
from .metrics import record_call, get_metrics
from .audit import record_audit, get_audit_log
from .stemmer import stem
from .synonyms import expand_synonyms, get_synonym_group

__all__ = [
    "get_logger",
    "strip_secrets",
    "DedupMap",
    "CircuitBreaker",
    "record_call",
    "get_metrics",
    "record_audit",
    "get_audit_log",
    "stem",
    "expand_synonyms",
    "get_synonym_group",
    "load_json_file",
]


def load_json_file(path: Path, default=None):
    """Load JSON from path, returning default if missing/corrupt."""
    if not path.exists():
        return default if default is not None else []
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return default if default is not None else []
