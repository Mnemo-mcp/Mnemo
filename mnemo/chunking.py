"""Chunking shim — kept for backward compatibility.

Chunking is no longer needed since engine/ handles indexing directly.
These are no-op stubs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chunk:
    id: str = ""
    chunk_type: str = ""
    path: str = ""
    language: str = ""
    symbol: str = ""
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def make_code_chunks(source: str, language: str = "", path: str = "") -> list[Chunk]:
    """No-op stub."""
    return []


def markdown_heading_chunks(text: str, path: str = "") -> list[Chunk]:
    """No-op stub."""
    return []


def api_endpoint_chunk(method: str, path: str, handler: str, file: str) -> Chunk:
    """No-op stub."""
    return Chunk()
