"""Memory vector indexing — embeds memories into the dense vector index."""

from __future__ import annotations

from pathlib import Path
from typing import Any

MEMORY_NAMESPACE = "memory"


def _memory_to_chunk(entry: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a memory entry to an indexable chunk."""
    content = entry.get("content", "")
    if not content:
        return None
    return {
        "id": f"memory-{entry.get('id', 0)}",
        "content": content,
        "metadata": {"category": entry.get("category", "general")},
    }


def _index_memory_entry(repo_root: Path, entry: dict[str, Any]) -> None:
    """Embed and index a single memory entry."""
    chunk = _memory_to_chunk(entry)
    if chunk:
        from ..retrieval import index_chunks
        index_chunks(repo_root, MEMORY_NAMESPACE, [chunk])
