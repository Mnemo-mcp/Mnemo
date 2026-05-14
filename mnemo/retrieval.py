"""Semantic retrieval orchestration."""

from __future__ import annotations

import threading
from pathlib import Path

from .chunking import Chunk
from .vector_index import LocalVectorIndex

_INDICES: dict[str, LocalVectorIndex] = {}
_LOCK = threading.Lock()


def get_index(repo_root: Path) -> LocalVectorIndex:
    key = str(repo_root.resolve())
    with _LOCK:
        if key not in _INDICES:
            _INDICES[key] = LocalVectorIndex(repo_root)
        return _INDICES[key]


def index_chunks(repo_root: Path, namespace: str, chunks: list[Chunk]) -> None:
    get_index(repo_root).upsert(namespace, chunks)


def semantic_query(
    repo_root: Path,
    namespace: str,
    query: str,
    limit: int = 10,
    filters: dict[str, str] | None = None,
) -> list[dict]:
    return get_index(repo_root).query(namespace, query, limit=limit, filters=filters)


def delete_chunks(repo_root: Path, namespace: str, file_path: str) -> None:
    """Delete all chunks for a removed file from the index."""
    idx = get_index(repo_root)
    # Remove from in-memory store
    records = idx._memory_store.get(namespace, [])
    idx._memory_store[namespace] = [r for r in records if r.metadata.get("path") != file_path]
    # Remove from ChromaDB
    collection = idx._collection(namespace)
    if collection:
        try:
            collection.delete(where={"path": file_path})
        except Exception:
            pass
