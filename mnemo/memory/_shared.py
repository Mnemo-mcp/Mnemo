"""Shared constants and utilities for the memory package."""

from __future__ import annotations

import re
import subprocess  # nosec B404
import time
from pathlib import Path
from typing import Any

from ..utils.logger import get_logger

logger = get_logger("memory")

# --- Output and budget constants ---
MAX_OUTPUT_CHARS = 75000
RECALL_BUDGET = 12000
MEMORY_TOKEN_BUDGET = 1000
TOKEN_CHAR_RATIO = 4

# --- Tier thresholds (seconds) ---
# Memories accessed within 7 days are "hot" (included in recall)
HOT_THRESHOLD = 7 * 24 * 3600  # 7 days in seconds
# Memories not accessed for 30+ days become "cold" (eviction candidates)
WARM_THRESHOLD = 30 * 24 * 3600  # 30 days in seconds

# --- Categories that are never evicted ---
PINNED_CATEGORIES = {"architecture", "preference", "decision"}

# --- Auto-categorization patterns ---
_CATEGORY_PATTERNS = {
    "bug": re.compile(
        r"\b(fix|bug|error|crash|null|exception|broken|issue|regression|failed)\b", re.I
    ),
    "architecture": re.compile(
        r"\b(chose|decided|architecture|design|pattern|structure|migrate|refactor)\b", re.I
    ),
    "preference": re.compile(
        r"\b(always|never|convention|naming|prefer|style|standard|rule)\b", re.I
    ),
    "todo": re.compile(
        r"\b(todo|later|follow.?up|need to|should|plan|future|next)\b", re.I
    ),
    "pattern": re.compile(
        r"\b(pattern|similar|handler|implements|base class|interface|abstract)\b", re.I
    ),
}

# --- Vector index namespace ---
MEMORY_NAMESPACE = "memory"

# --- Retention and dedup thresholds ---
# Memories with 50+ entries trigger compression/consolidation
COMPRESS_THRESHOLD = 50
# Similarity above 0.85 = duplicate content (skip storage)
DEDUP_SIMILARITY_THRESHOLD = 0.85
# Similarity 0.5-0.85 between decisions = potential contradiction
CONTRADICTION_SIMILARITY_THRESHOLD = 0.5

# --- Mutation hook state ---
_REFRESH_COOLDOWN = 5.0
_last_refresh_time: float = 0
_on_mutate_hook: "list[Any]" = []

# --- Tag extraction patterns ---
_TAG_PATTERNS = {
    "code": re.compile(r'[\w/]+\.\w{1,5}\b|[\w]+/[\w/]+\.\w+'),
    "debugging": re.compile(r'\b(error|exception|traceback|stack.?trace|crash|bug|fix)\b', re.I),
    "architecture": re.compile(r'\b(architecture|design|pattern|service|module|layer|component)\b', re.I),
}

# --- Category importance weights ---
_IMPORTANCE_MAP = {
    "architecture": 5, "decision": 5, "preference": 4, "pattern": 4, "bug": 3, "general": 2, "todo": 2,
}

# --- File path detection ---
_FILE_PATH_RE = re.compile(r'(?:[\w./\\-]+/[\w./\\-]+\.(?:py|js|ts|tsx|jsx|go|rs|java|cs|rb|php|c|cpp|h|hpp|kt|swift|scala|json|yaml|yml|toml|md|sh))\b')

# --- Stop words for text processing ---
_STOP_WORDS = frozenset("the a an is are was were be been being have has had do does did will would shall should may might can could this that these those it its i we you they he she".split())


# --- Pure helper functions ---

def _ensure_list(data: Any) -> list[dict[str, Any]]:
    """Coerce data to list — returns empty list if data is not a list."""
    return data if isinstance(data, list) else []


def _ensure_dict(data: Any) -> dict[str, Any]:
    """Coerce data to dict — returns empty dict if data is not a dict."""
    return data if isinstance(data, dict) else {}


# Backward-compatible aliases
_as_list = _ensure_list
_as_dict = _ensure_dict


def _next_id(entries: list[dict[str, Any]]) -> int:
    """Generate the next unique ID from existing entries."""
    if not entries:
        return 1
    return max(e.get("id", 0) for e in entries) + 1


def _get_current_branch(repo_root: Path) -> str:
    """Get current git branch name."""
    try:
        result = subprocess.run(  # nosec B603 B607
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True, text=True, cwd=str(repo_root), timeout=2,
        )
        return result.stdout.strip() if result.returncode == 0 else 'main'
    except Exception:
        return 'main'


def _text_similarity(a: str, b: str) -> float:
    """Similarity using SparseEmbedding (IDF-weighted token overlap)."""
    from ..embeddings import KeywordEmbeddingProvider
    provider = KeywordEmbeddingProvider()
    emb_a = provider.embed(a)
    emb_b = provider.embed(b)
    return emb_a.score(emb_b)


# --- Re-exports from new modules (backward compatibility) ---
from .indexing import _memory_to_chunk, _index_memory_entry  # noqa: E402, F401
from .linking import _graph_link_entry  # noqa: E402, F401


# --- Mutation hook management ---

def register_on_mutate(callback) -> None:
    """Register a callback to be invoked after memory mutations (debounced)."""
    _on_mutate_hook.append(callback)


def _refresh_rule(repo_root: Path) -> None:
    """Invoke registered mutation hooks (debounced)."""
    global _last_refresh_time
    now = time.time()
    if now - _last_refresh_time < _REFRESH_COOLDOWN:
        return
    _last_refresh_time = now
    for hook in _on_mutate_hook:
        try:
            hook(repo_root)
        except Exception as exc:
            logger.debug(f"Mutation hook failed: {exc}")
