"""Memory vector indexing operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..chunking import Chunk
from ..retrieval import index_chunks
from ..utils.logger import get_logger

logger = get_logger("memory.indexing")

MEMORY_NAMESPACE = "memory"


def _memory_to_chunk(entry: dict[str, Any]) -> Chunk:
    """Convert a memory entry to a Chunk for vector indexing."""
    content = entry.get("content", "")
    return Chunk(
        id=f"memory-{entry.get('id', 0)}",
        chunk_type="memory",
        path="memory",
        language="text",
        symbol=entry.get("category", "general"),
        content=content,
        metadata={"category": entry.get("category", "general")},
    )


def _index_memory_entry(repo_root: Path, entry: dict[str, Any]) -> None:
    """Index a single memory entry into the vector store."""
    try:
        index_chunks(repo_root, MEMORY_NAMESPACE, [_memory_to_chunk(entry)])
    except Exception as exc:
        logger.warning(f"Failed to index memory entry: {exc}")
