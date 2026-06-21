"""Injection detection patterns — shared across all write paths."""
import re
from typing import Optional

# Patterns that detect prompt injection / instruction hijacking
INJECTION_PATTERNS = [
    re.compile(r'ignore\s+(all\s+)?previous\s+(instructions|context|rules)', re.I),
    re.compile(r'you\s+are\s+now\s+', re.I),
    re.compile(r'always\s+output\s+no\s+findings', re.I),
    re.compile(r'skip\s+(all\s+)?(security|review|checks)', re.I),
    re.compile(r'override[:\s]', re.I),
    re.compile(r'\bsystem\s*:', re.I),
    re.compile(r'\bassistant\s*:', re.I),
    re.compile(r'\buser\s*:', re.I),
    re.compile(r'\bhuman\s*:', re.I),
    re.compile(r'disregard\s+(all\s+)?(previous|above|prior)', re.I),
    re.compile(r'from\s+now\s+on\b', re.I),
    re.compile(r'do\s+not\s+(report|flag|mention)', re.I),
    re.compile(r'approve\s+(all|every|this)', re.I),
    re.compile(r'<\|?(im_start|im_end|endoftext)\|?>', re.I),
    re.compile(r'\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>', re.I),
]


def has_injection(text: str) -> bool:
    """Check if text contains instruction-like patterns that could hijack an agent."""
    return any(p.search(text) for p in INJECTION_PATTERNS)


def first_injection_match(text: str) -> Optional[str]:
    """Return the first matching injection pattern for error messages."""
    for p in INJECTION_PATTERNS:
        m = p.search(text)
        if m:
            return m.group(0)
    return None
