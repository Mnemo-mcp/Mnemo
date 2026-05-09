from pathlib import Path

from mnemo.chunking import api_endpoint_chunk, make_code_chunks, markdown_heading_chunks
from mnemo.retrieval import get_index, index_chunks, semantic_query


def test_make_code_chunks_builds_class_and_function_chunks():
    chunks = make_code_chunks(
        "src/service.py",
        "python",
        {"classes": [{"name": "OrderService", "methods": ["create()", "cancel()"]}], "functions": ["def helper(x)"]},
    )
    assert any(chunk.symbol == "OrderService" for chunk in chunks)
    assert any(chunk.symbol == "helper" for chunk in chunks)


def test_markdown_heading_chunks(tmp_path: Path):
    kdir = tmp_path / ".mnemo" / "knowledge"
    kdir.mkdir(parents=True)
    doc = kdir / "architecture.md"
    doc.write_text("# Architecture\nUses handlers\n## Risks\nQueue lag", encoding="utf-8")
    chunks = markdown_heading_chunks(kdir, doc)
    assert len(chunks) >= 2
    assert chunks[0].chunk_type == "knowledge"


def test_semantic_query_has_fallback_without_chroma(tmp_path: Path):
    chunk = api_endpoint_chunk("api/openapi.json", "GET", "/orders/{id}", "Fetch order")
    index_chunks(tmp_path, "api", [chunk])
    results = semantic_query(tmp_path, "api", "fetch order endpoint", limit=3)
    assert results
    assert "/orders/{id}" in results[0]["content"]
    assert get_index(tmp_path) is not None
