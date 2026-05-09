"""Embedding provider abstractions for local semantic retrieval."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import Protocol


def _tokenize(text: str) -> list[str]:
    normalized = text.lower().replace("_", " ")
    return re.findall(r"[a-zA-Z0-9]+", normalized)


@dataclass(frozen=True)
class SparseEmbedding:
    """Lightweight token-count embedding used for fallback retrieval."""

    counts: dict[str, int]

    def score(self, other: "SparseEmbedding") -> float:
        if not self.counts or not other.counts:
            return 0.0
        overlap = sum(min(self.counts.get(tok, 0), other.counts.get(tok, 0)) for tok in self.counts)
        norm = max(sum(self.counts.values()), 1)
        return overlap / norm


class EmbeddingProvider(Protocol):
    """Embedding provider protocol."""

    def embed(self, text: str) -> SparseEmbedding:
        ...

    def embed_many(self, texts: list[str]) -> list[SparseEmbedding]:
        ...


class KeywordEmbeddingProvider:
    """Cheap keyword provider used as default and in tests."""

    def embed(self, text: str) -> SparseEmbedding:
        return SparseEmbedding(dict(Counter(_tokenize(text))))

    def embed_many(self, texts: list[str]) -> list[SparseEmbedding]:
        return [self.embed(text) for text in texts]
