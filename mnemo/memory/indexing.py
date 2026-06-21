"""Memory vector indexing — embeds memories into the dense vector index."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ._shared import MEMORY_NAMESPACE


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
        from ..embeddings import get_keyword_provider, save_keyword_state
        index_chunks(repo_root, MEMORY_NAMESPACE, [chunk])
        # Update BM25 IDF stats
        provider = get_keyword_provider(repo_root)
        provider.update_corpus([chunk["content"]])
        save_keyword_state(repo_root)
