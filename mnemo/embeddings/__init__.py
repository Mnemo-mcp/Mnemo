"""Embedding provider abstractions for local semantic retrieval."""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Protocol

from ..utils.stemmer import stem
from ..utils.synonyms import expand_synonyms


def _tokenize(text: str) -> list[str]:
    normalized = text.lower().replace("_", " ")
    tokens = re.findall(r"[a-zA-Z0-9]+", normalized)
    return [stem(t) for t in tokens]


@dataclass(frozen=True)
class SparseEmbedding:
    """Lightweight token-count embedding with optional IDF weighting."""

    counts: dict[str, float]

    def score(self, other: "SparseEmbedding") -> float:
        if not self.counts or not other.counts:
            return 0.0
        overlap = sum(
            min(self.counts.get(tok, 0), other.counts.get(tok, 0))
            for tok in self.counts
        )
        norm = max(sum(self.counts.values()), 1)
        return overlap / norm


class EmbeddingProvider(Protocol):
    """Embedding provider protocol."""

    def embed(self, text: str) -> SparseEmbedding:
        ...

    def embed_many(self, texts: list[str]) -> list[SparseEmbedding]:
        ...


class KeywordEmbeddingProvider:
    """Keyword provider with IDF weighting for better relevance."""

    def __init__(self):
        self._doc_freq: Counter = Counter()
        self._total_docs: int = 0

    def update_corpus(self, texts: list[str]) -> None:
        """Update IDF statistics from a batch of documents."""
        for text in texts:
            unique_tokens = set(_tokenize(text))
            self._doc_freq.update(unique_tokens)
            self._total_docs += 1

    def _idf(self, token: str) -> float:
        if self._total_docs == 0:
            return 1.0
        df = self._doc_freq.get(token, 0)
        return math.log((self._total_docs + 1) / (df + 1)) + 1.0

    def embed(self, text: str) -> SparseEmbedding:
        tokens = _tokenize(text)
        counts = Counter(tokens)
        # Expand with synonyms at 0.7x weight
        for term, weight in expand_synonyms(list(counts.keys())):
            if term not in counts:
                counts[term] = 0.7 * weight
        if self._total_docs > 0:
            weighted = {tok: count * self._idf(tok) for tok, count in counts.items()}
        else:
            weighted = dict(counts)
        return SparseEmbedding(weighted)

    def embed_many(self, texts: list[str]) -> list[SparseEmbedding]:
        return [self.embed(text) for text in texts]

    def save_state(self, path: Path) -> None:
        """Serialize IDF state to JSON."""
        data = {"doc_freq": dict(self._doc_freq), "total_docs": self._total_docs}
        path.write_text(json.dumps(data))

    def load_state(self, path: Path) -> bool:
        """Restore IDF state from JSON. Returns True if successful."""
        try:
            data = json.loads(path.read_text())
            self._doc_freq = Counter(data["doc_freq"])
            self._total_docs = data["total_docs"]
            return True
        except Exception:
            return False
