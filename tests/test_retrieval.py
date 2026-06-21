"""Tests for mnemo/retrieval.py — vector index integration tests."""

import json

import numpy as np
import pytest

try:
    from mnemo.embeddings.dense import embed, embed_one
    HAS_EMBEDDINGS = True
except Exception:
    HAS_EMBEDDINGS = False

from mnemo.retrieval import index_chunks, semantic_query, remove_chunk, delete_chunks, _index_path

needs_embeddings = pytest.mark.skipif(not HAS_EMBEDDINGS, reason="ONNX embeddings not available")


@pytest.fixture
def repo(tmp_path):
    (tmp_path / ".mnemo").mkdir()
    return tmp_path


@needs_embeddings
class TestIndexChunks:
    def test_stores_vectors_and_metadata(self, repo):
        chunks = [
            {"id": "c1", "content": "Python is a programming language"},
            {"id": "c2", "content": "Rust is a systems language"},
        ]
        index_chunks(repo, "test", chunks)

        vec_path, meta_path = _index_path(repo, "test")
        vecs = np.load(vec_path)
        meta = json.loads(meta_path.read_text())

        assert vecs.shape == (2, 384)
        assert len(meta) == 2
        assert meta[0]["id"] == "c1"
        assert meta[1]["id"] == "c2"

    def test_deduplicates_by_id(self, repo):
        chunks = [{"id": "dup", "content": "Hello world"}]
        index_chunks(repo, "test", chunks)
        index_chunks(repo, "test", chunks)  # same ID again

        vec_path, meta_path = _index_path(repo, "test")
        meta = json.loads(meta_path.read_text())
        assert len(meta) == 1

    def test_empty_chunks_noop(self, repo):
        index_chunks(repo, "test", [])
        vec_path, _ = _index_path(repo, "test")
        assert not vec_path.exists()


@needs_embeddings
class TestSemanticQuery:
    @pytest.fixture(autouse=True)
    def _seed(self, repo):
        chunks = [
            {"id": "py", "content": "Python is a high-level programming language used for web development and data science", "metadata": {"lang": "python"}},
            {"id": "go", "content": "Golang is a compiled language by Google designed for concurrency and networking", "metadata": {"lang": "go"}},
            {"id": "recipe", "content": "To bake a chocolate cake mix flour sugar cocoa butter and eggs", "metadata": {"lang": "none"}},
        ]
        index_chunks(repo, "test", chunks)

    def test_returns_relevant_results(self, repo):
        results = semantic_query(repo, "test", "Python programming")
        assert len(results) > 0
        assert results[0]["id"] == "py"

    def test_with_filters(self, repo):
        results = semantic_query(repo, "test", "programming language", filters={"lang": "go"})
        assert all(r["id"] == "go" for r in results if r.get("score", 0) > 0.05)

    def test_no_results_for_missing_namespace(self, repo):
        results = semantic_query(repo, "nonexistent", "anything")
        assert results == []


@needs_embeddings
class TestRemoveChunk:
    def test_removes_correct_entry(self, repo):
        chunks = [
            {"id": "a", "content": "Alpha content"},
            {"id": "b", "content": "Beta content"},
            {"id": "c", "content": "Gamma content"},
        ]
        index_chunks(repo, "test", chunks)

        assert remove_chunk(repo, "test", "b") is True

        _, meta_path = _index_path(repo, "test")
        meta = json.loads(meta_path.read_text())
        ids = [m["id"] for m in meta]
        assert "b" not in ids
        assert "a" in ids and "c" in ids

    def test_returns_false_for_missing_id(self, repo):
        index_chunks(repo, "test", [{"id": "x", "content": "exists"}])
        assert remove_chunk(repo, "test", "missing") is False

    def test_returns_false_on_empty_index(self, repo):
        assert remove_chunk(repo, "test", "anything") is False


@needs_embeddings
class TestDeleteChunks:
    def test_removes_all_files(self, repo):
        index_chunks(repo, "test", [{"id": "d1", "content": "data"}])
        vec_path, meta_path = _index_path(repo, "test")
        assert vec_path.exists()

        delete_chunks(repo, "test")
        assert not vec_path.exists()
        assert not meta_path.exists()


@needs_embeddings
class TestRoundTrip:
    def test_index_remove_query(self, repo):
        chunks = [
            {"id": "dog", "content": "Dogs are loyal pets that love to play fetch"},
            {"id": "cat", "content": "Cats are independent animals that like to nap"},
            {"id": "fish", "content": "Fish swim in water and need an aquarium"},
        ]
        index_chunks(repo, "test", chunks)

        remove_chunk(repo, "test", "cat")

        results = semantic_query(repo, "test", "pets animals")
        result_ids = [r["id"] for r in results]
        assert "cat" not in result_ids
        assert "dog" in result_ids
