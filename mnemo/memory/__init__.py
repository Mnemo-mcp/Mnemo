"""Persistent memory store with tiered retrieval and auto-categorization.

Public API re-exports for the memory package.
"""

from __future__ import annotations

# --- Public API ---
from .store import add_memory, forget_memory, add_decision, save_context
from .retention import compress_memory, detect_contradictions, bulk_forget, auto_forget_sweep
from .search import search_memory, lookup, recall

# --- Constants (public) ---
from ._shared import (
    MAX_OUTPUT_CHARS,
    RECALL_BUDGET,
    MEMORY_TOKEN_BUDGET,
    TOKEN_CHAR_RATIO,
    HOT_THRESHOLD,
    WARM_THRESHOLD,
    PINNED_CATEGORIES,
    MEMORY_NAMESPACE,
    COMPRESS_THRESHOLD,
    DEDUP_SIMILARITY_THRESHOLD,
    CONTRADICTION_SIMILARITY_THRESHOLD,
    register_on_mutate,
)

# --- Semi-public (used by tests and sibling packages) ---
from ._shared import _get_current_branch, _text_similarity, _as_list, _as_dict, _next_id  # noqa: F401
from .retention import _compute_retention, _get_tier
from .search import _recall_memory, _recall_repo_map  # noqa: F401

__all__ = [
    # Public API
    "add_memory", "forget_memory", "add_decision", "save_context",
    "compress_memory", "detect_contradictions", "bulk_forget", "auto_forget_sweep",
    "search_memory", "lookup", "recall",
    # Constants
    "MAX_OUTPUT_CHARS", "RECALL_BUDGET", "MEMORY_TOKEN_BUDGET", "TOKEN_CHAR_RATIO",
    "HOT_THRESHOLD", "WARM_THRESHOLD", "PINNED_CATEGORIES", "MEMORY_NAMESPACE",
    "COMPRESS_THRESHOLD", "DEDUP_SIMILARITY_THRESHOLD", "CONTRADICTION_SIMILARITY_THRESHOLD",
    "register_on_mutate",
    # Semi-public (tests)
    "_get_current_branch", "_text_similarity", "_compute_retention", "_get_tier", "_recall_memory",
]
