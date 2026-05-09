"""Local vector index with optional ChromaDB backend."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from ..chunking import Chunk
from ..embeddings import KeywordEmbeddingProvider


class VectorIndex(Protocol):
    def available(self) -> bool:
        ...

    def upsert(self, namespace: str, chunks: list[Chunk]) -> None:
        ...

    def query(self, namespace: str, query: str, limit: int = 10, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        ...

    def clear(self, namespace: str | None = None) -> None:
        ...


@dataclass
class _MemoryRecord:
    id: str
    text: str
    metadata: dict[str, Any]


class LocalVectorIndex:
    """Chroma-first index with in-memory keyword fallback."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.index_dir = repo_root / ".mnemo" / "index"
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._fallback = KeywordEmbeddingProvider()
        self._memory_store: dict[str, list[_MemoryRecord]] = {}
        self._chroma_collection_cache: dict[str, Any] = {}
        self._chroma_client: Any = None
        self._chroma_ready = False
        self._init_chroma()

    def _init_chroma(self) -> None:
        try:
            import chromadb
        except Exception:
            self._chroma_ready = False
            return
        try:
            self._chroma_client = chromadb.PersistentClient(path=str(self.index_dir / "chroma"))
            self._chroma_ready = True
        except Exception:
            self._chroma_ready = False

    def _collection(self, namespace: str):
        if not self._chroma_ready or self._chroma_client is None:
            return None
        if namespace not in self._chroma_collection_cache:
            self._chroma_collection_cache[namespace] = self._chroma_client.get_or_create_collection(
                name=namespace
            )
        return self._chroma_collection_cache[namespace]

    def available(self) -> bool:
        return self._chroma_ready

    def upsert(self, namespace: str, chunks: list[Chunk]) -> None:
        self._memory_store[namespace] = [
            _MemoryRecord(
                id=chunk.id,
                text=f"{chunk.path} {chunk.symbol}\n{chunk.content}",
                metadata={**chunk.metadata, "path": chunk.path, "symbol": chunk.symbol, "chunk_type": chunk.chunk_type},
            )
            for chunk in chunks
        ]
        collection = self._collection(namespace)
        if not collection:
            return
        if chunks:
            collection.upsert(
                ids=[chunk.id for chunk in chunks],
                documents=[f"{chunk.path} {chunk.symbol}\n{chunk.content}" for chunk in chunks],
                metadatas=[
                    {
                        "path": chunk.path,
                        "language": chunk.language,
                        "symbol": chunk.symbol,
                        "chunk_type": chunk.chunk_type,
                        **chunk.metadata,
                    }
                    for chunk in chunks
                ],
            )

    def _query_fallback(self, namespace: str, query: str, limit: int, filters: dict[str, Any] | None) -> list[dict[str, Any]]:
        query_emb = self._fallback.embed(query)
        records = self._memory_store.get(namespace, [])
        scored: list[tuple[float, _MemoryRecord]] = []
        for record in records:
            if filters and any(record.metadata.get(k) != v for k, v in filters.items()):
                continue
            score = query_emb.score(self._fallback.embed(record.text))
            if score > 0:
                scored.append((score, record))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {"id": record.id, "score": score, "content": record.text, "metadata": record.metadata}
            for score, record in scored[:limit]
        ]

    def query(self, namespace: str, query: str, limit: int = 10, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        collection = self._collection(namespace)
        if not collection:
            return self._query_fallback(namespace, query, limit, filters)
        try:
            where = filters or None
            result = collection.query(query_texts=[query], n_results=limit, where=where)
            ids = result.get("ids", [[]])[0]
            docs = result.get("documents", [[]])[0]
            distances = result.get("distances", [[]])[0] if result.get("distances") else [0.0] * len(ids)
            metas = result.get("metadatas", [[]])[0] if result.get("metadatas") else [{} for _ in ids]
            return [
                {"id": doc_id, "score": 1.0 - float(dist), "content": doc, "metadata": meta}
                for doc_id, doc, dist, meta in zip(ids, docs, distances, metas)
            ]
        except Exception:
            return self._query_fallback(namespace, query, limit, filters)

    def clear(self, namespace: str | None = None) -> None:
        if namespace is None:
            self._memory_store.clear()
            self._chroma_collection_cache.clear()
            return
        self._memory_store.pop(namespace, None)
        self._chroma_collection_cache.pop(namespace, None)
