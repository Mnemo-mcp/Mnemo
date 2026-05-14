"""Shared utilities — logging, privacy, dedup, metrics, circuit breaker, audit."""

from __future__ import annotations

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
]
