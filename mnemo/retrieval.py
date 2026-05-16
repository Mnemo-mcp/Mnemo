"""Retrieval — dense vector index using ONNX embeddings + numpy cosine search."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .config import mnemo_path


def _index_path(repo_root: Path, namespace: str) -> tuple[Path, Path]:
    """Return (vectors.npy, meta.json) paths for a namespace."""
    base = mnemo_path(repo_root)
    return base / f"vectors_{namespace}.npy", base / f"meta_{namespace}.json"


def index_chunks(repo_root: Path, namespace: str, chunks: list) -> None:
    """Embed and store chunks in the vector index."""
    if not chunks:
        return

    from .embeddings.dense import embed

    vec_path, meta_path = _index_path(repo_root, namespace)

    # Load existing
    existing_vecs = np.load(vec_path) if vec_path.exists() else np.zeros((0, 384), dtype=np.float32)
    existing_meta = json.loads(meta_path.read_text()) if meta_path.exists() else []

    # Prepare new texts
    texts = []
    metas = []
    existing_ids = {m.get("id") for m in existing_meta}
    for chunk in chunks:
        chunk_id = chunk.get("id", f"{namespace}-{len(existing_meta) + len(texts)}")
        if chunk_id in existing_ids:
            continue
        text = chunk.get("content") or chunk.get("text") or ""
        if not text:
            continue
        texts.append(text)
        metas.append({"id": chunk_id, "content": text[:500], "metadata": chunk.get("metadata", {})})

    if not texts:
        return

    new_vecs = embed(texts)
    all_vecs = np.vstack([existing_vecs, new_vecs]) if existing_vecs.size else new_vecs
    all_meta = existing_meta + metas

    np.save(vec_path, all_vecs)
    meta_path.write_text(json.dumps(all_meta))


def semantic_query(repo_root: Path, namespace: str, query: str, top_k: int = 5, limit: int = 5, **kwargs) -> list[dict[str, Any]]:
    """Search the vector index for the most similar chunks."""
    from .embeddings.dense import embed_one

    vec_path, meta_path = _index_path(repo_root, namespace)
    if not vec_path.exists() or not meta_path.exists():
        return []

    vectors = np.load(vec_path)
    if vectors.size == 0:
        return []

    meta = json.loads(meta_path.read_text())
    k = limit or top_k

    query_vec = embed_one(query)
    scores = vectors @ query_vec  # cosine similarity (vectors are normalized)

    # Apply filters if provided
    filters = kwargs.get("filters")
    if filters:
        for i, m in enumerate(meta):
            md = m.get("metadata", {})
            for fk, fv in filters.items():
                if md.get(fk) != fv:
                    scores[i] = -1.0

    top_indices = np.argsort(scores)[::-1][:k]
    results = []
    for idx in top_indices:
        if scores[idx] < 0.05:  # minimum similarity threshold
            break
        entry = meta[idx].copy()
        entry["score"] = float(scores[idx])
        results.append(entry)

    return results


def delete_chunks(repo_root: Path, namespace: str) -> None:
    """Delete the vector index for a namespace."""
    vec_path, meta_path = _index_path(repo_root, namespace)
    vec_path.unlink(missing_ok=True)
    meta_path.unlink(missing_ok=True)
