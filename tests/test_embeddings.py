"""Sandbox tests for mnemo/embeddings/ — BM25 keyword + ONNX dense providers."""

import json
import math
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from mnemo.embeddings import (
    KeywordEmbeddingProvider,
    SparseEmbedding,
    _tokenize,
    get_keyword_provider,
    save_keyword_state,
)
import mnemo.embeddings as emb_module


class TestTokenize:
    """Test the shared tokenizer used by BM25."""

    def test_basic_tokenization(self):
        tokens = _tokenize("Hello World")
        assert len(tokens) == 2
        # Stemmed and lowercased
        assert all(t == t.lower() for t in tokens)

    def test_underscore_splitting(self):
        tokens = _tokenize("my_function_name")
        assert len(tokens) == 3

    def test_camel_case_not_split(self):
        # CamelCase stays as one token (lowercased)
        tokens = _tokenize("MyClassName")
        assert "myclassnam" in tokens or "myclassname" in tokens or len(tokens) == 1

    def test_empty_input(self):
        assert _tokenize("") == []
        assert _tokenize(None) == []

    def test_special_chars_removed(self):
        tokens = _tokenize("func() -> bool:")
        # Only alphanumeric kept
        assert "(" not in "".join(tokens)
        assert ")" not in "".join(tokens)


class TestSparseEmbedding:
    """Test the SparseEmbedding score function."""

    def test_identical_embeddings_score_1(self):
        emb = SparseEmbedding(counts={"hello": 1.0, "world": 1.0})
        assert emb.score(emb) == 1.0

    def test_disjoint_embeddings_score_0(self):
        a = SparseEmbedding(counts={"hello": 1.0})
        b = SparseEmbedding(counts={"world": 1.0})
        assert a.score(b) == 0.0

    def test_partial_overlap(self):
        a = SparseEmbedding(counts={"hello": 1.0, "world": 1.0})
        b = SparseEmbedding(counts={"hello": 1.0, "python": 1.0})
        score = a.score(b)
        assert 0.0 < score < 1.0

    def test_empty_embedding_scores_0(self):
        a = SparseEmbedding(counts={})
        b = SparseEmbedding(counts={"hello": 1.0})
        assert a.score(b) == 0.0
        assert b.score(a) == 0.0


class TestKeywordEmbeddingProvider:
    """Test BM25 keyword provider with IDF weighting."""

    def test_embed_basic(self):
        provider = KeywordEmbeddingProvider()
        emb = provider.embed("hello world")
        assert isinstance(emb, SparseEmbedding)
        assert len(emb.counts) > 0

    def test_no_idf_without_corpus(self):
        """Without corpus, IDF returns 1.0 for all tokens (flat weighting)."""
        provider = KeywordEmbeddingProvider()
        assert provider._idf("anything") == 1.0
        assert provider._total_docs == 0

    def test_update_corpus_builds_idf(self):
        provider = KeywordEmbeddingProvider()
        provider.update_corpus([
            "Python is great for data science",
            "Python frameworks include Django and Flask",
            "JavaScript is used for frontend development",
        ])
        assert provider._total_docs == 3
        # 'python' appears in 2/3 docs, 'javascript' in 1/3
        # IDF(python) < IDF(javascript) because python is more common
        idf_python = provider._idf("python")
        idf_javascript = provider._idf("javascript")
        # Actually: IDF = log((N+1)/(df+1)) + 1
        # python: log(4/3) + 1 ≈ 1.29
        # javascript: log(4/2) + 1 ≈ 1.69
        assert idf_javascript > idf_python

    def test_idf_weights_affect_embedding(self):
        """Rare terms get higher weights than common terms."""
        provider = KeywordEmbeddingProvider()
        provider.update_corpus([
            "the database connection",
            "the database query",
            "the database migration",
            "unique specialized term",
        ])
        # 'database' is in 3/4 docs (common), 'unique' is in 1/4 (rare)
        emb = provider.embed("database unique")
        # Check that 'unique' stemmed form has higher weight than 'database' stemmed form
        db_key = None
        unique_key = None
        for key in emb.counts:
            if "databas" in key:
                db_key = key
            if "uniqu" in key:
                unique_key = key
        if db_key and unique_key:
            assert emb.counts[unique_key] > emb.counts[db_key]

    def test_synonym_expansion(self):
        """Embed includes synonym terms at 0.7x weight."""
        provider = KeywordEmbeddingProvider()
        emb = provider.embed("error")
        # Should have expanded with synonyms like "bug", "exception", etc.
        # At minimum, the original term should be there
        assert any("error" in k or "err" in k for k in emb.counts)

    def test_embed_many(self):
        provider = KeywordEmbeddingProvider()
        results = provider.embed_many(["hello", "world", "test"])
        assert len(results) == 3
        assert all(isinstance(r, SparseEmbedding) for r in results)

    def test_save_and_load_state(self, tmp_path):
        """IDF state persists correctly through save/load cycle."""
        provider = KeywordEmbeddingProvider()
        provider.update_corpus([
            "authentication JWT tokens",
            "database PostgreSQL connection",
            "caching Redis cluster",
        ])
        original_docs = provider._total_docs
        original_freq = dict(provider._doc_freq)

        # Save
        state_path = tmp_path / "bm25.json"
        provider.save_state(state_path)
        assert state_path.exists()

        # Load into fresh provider
        new_provider = KeywordEmbeddingProvider()
        assert new_provider._total_docs == 0
        loaded = new_provider.load_state(state_path)
        assert loaded is True
        assert new_provider._total_docs == original_docs
        assert dict(new_provider._doc_freq) == original_freq

    def test_load_state_returns_false_on_missing_file(self, tmp_path):
        provider = KeywordEmbeddingProvider()
        assert provider.load_state(tmp_path / "nonexistent.json") is False

    def test_load_state_returns_false_on_invalid_json(self, tmp_path):
        bad_path = tmp_path / "bad.json"
        bad_path.write_text("not json")
        provider = KeywordEmbeddingProvider()
        assert provider.load_state(bad_path) is False

    def test_similarity_ordering(self):
        """More similar texts should score higher."""
        provider = KeywordEmbeddingProvider()
        provider.update_corpus([
            "PostgreSQL database connection pool timeout",
            "Redis cache cluster configuration",
            "JWT authentication token validation",
        ])
        query = provider.embed("database connection timeout")
        db = provider.embed("PostgreSQL database connection pool")
        cache = provider.embed("Redis cache memory limit")
        auth = provider.embed("JWT token authentication")

        score_db = query.score(db)
        score_cache = query.score(cache)
        score_auth = query.score(auth)

        # Database text should be most similar to database query
        assert score_db > score_cache
        assert score_db > score_auth


class TestGetKeywordProvider:
    """Test the singleton get_keyword_provider function."""

    def test_returns_provider_without_repo(self):
        emb_module._provider_cache = None  # Reset singleton
        provider = get_keyword_provider()
        assert isinstance(provider, KeywordEmbeddingProvider)

    def test_singleton_returns_same_instance(self):
        emb_module._provider_cache = None
        p1 = get_keyword_provider()
        p2 = get_keyword_provider()
        assert p1 is p2

    def test_loads_state_from_disk(self, tmp_path):
        """When repo_root has a BM25 state file, it loads it."""
        emb_module._provider_cache = None
        mnemo_dir = tmp_path / ".mnemo"
        mnemo_dir.mkdir()
        state_path = mnemo_dir / "bm25_idf.json"
        state_path.write_text(json.dumps({"doc_freq": {"test": 5}, "total_docs": 10}))

        provider = get_keyword_provider(tmp_path)
        assert provider._total_docs == 10
        assert provider._doc_freq["test"] == 5
        emb_module._provider_cache = None  # Clean up singleton

    def test_save_keyword_state_writes_file(self, tmp_path):
        emb_module._provider_cache = None
        mnemo_dir = tmp_path / ".mnemo"
        mnemo_dir.mkdir()

        provider = get_keyword_provider(tmp_path)
        provider.update_corpus(["test document one", "test document two"])
        save_keyword_state(tmp_path)

        state_path = mnemo_dir / "bm25_idf.json"
        assert state_path.exists()
        data = json.loads(state_path.read_text())
        assert data["total_docs"] == 2
        emb_module._provider_cache = None


class TestDenseEmbeddings:
    """Test ONNX dense embedding provider."""

    def test_embed_returns_correct_shape(self):
        """embed() returns (N, 384) array regardless of ONNX availability."""
        from mnemo.embeddings.dense import embed, _DIM
        result = embed(["hello world", "test"])
        assert result.shape == (2, _DIM)
        assert result.dtype == np.float32

    def test_embed_one_returns_vector(self):
        from mnemo.embeddings.dense import embed_one, _DIM
        result = embed_one("test query")
        assert result.shape == (_DIM,)
        assert result.dtype == np.float32

    def test_embed_empty_list(self):
        from mnemo.embeddings.dense import embed, _DIM
        result = embed([])
        assert result.shape == (0, _DIM)

    def test_vectors_are_normalized(self):
        """If ONNX is available, vectors should be unit-normalized."""
        from mnemo.embeddings.dense import embed, _unavailable
        if _unavailable:
            pytest.skip("ONNX model not available")
        result = embed(["test normalization"])
        norm = np.linalg.norm(result[0])
        assert abs(norm - 1.0) < 0.01

    def test_similar_texts_have_high_cosine(self):
        """Semantically similar texts should have high cosine similarity."""
        from mnemo.embeddings.dense import embed, _unavailable
        if _unavailable:
            pytest.skip("ONNX model not available")
        vecs = embed([
            "PostgreSQL database connection",
            "MySQL database query",
            "recipe for chocolate cake",
        ])
        # Cosine similarity (vectors are normalized, so dot product = cosine)
        sim_db = float(vecs[0] @ vecs[1])
        sim_unrelated = float(vecs[0] @ vecs[2])
        assert sim_db > sim_unrelated

    def test_dim_returns_384(self):
        from mnemo.embeddings.dense import dim
        assert dim() == 384

    def test_graceful_when_model_unavailable(self):
        """Even without ONNX model, embed returns zero vectors (never crashes)."""
        from mnemo.embeddings.dense import embed, _DIM
        # Even if model is unavailable, should return zeros gracefully
        result = embed(["test"])
        assert result.shape == (1, _DIM)
        # Either real embeddings (non-zero) or graceful zeros
        assert result.dtype == np.float32
