"""Core security and storage primitives — shared across all Mnemo write and read paths."""
from .injection import has_injection, first_injection_match, INJECTION_PATTERNS
from .datamark import datamark, wrap_trust_envelope
from .store import append_jsonl, read_jsonl
from .atomic import atomic_write_json, atomic_read_json

__all__ = [
    'has_injection', 'first_injection_match', 'INJECTION_PATTERNS',
    'datamark', 'wrap_trust_envelope',
    'append_jsonl', 'read_jsonl',
    'atomic_write_json', 'atomic_read_json',
]
