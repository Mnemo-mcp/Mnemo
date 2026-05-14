"""SHA-256 tool call deduplication with TTL."""

from __future__ import annotations

import hashlib
import time


class DedupMap:
    """TTL-based dedup using SHA-256 hash of tool_name + tool_input."""


    def __init__(self):
        self._store: dict[str, float] = {}

    def is_duplicate(self, tool_name: str, tool_input: str, ttl: int = 300) -> bool:
        self.cleanup()
        key = hashlib.sha256((tool_name + tool_input[:500]).encode()).hexdigest()
        now = time.time()
        if key in self._store and now - self._store[key] < ttl:
            return True
        self._store[key] = now
        return False

    def cleanup(self) -> None:
        now = time.time()
        self._store = {k: v for k, v in self._store.items() if now - v < 600}


_dedup = DedupMap()
