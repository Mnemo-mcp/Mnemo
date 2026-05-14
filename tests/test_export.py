"""Tests for mnemo/export.py — Obsidian export."""
import json
import pytest
from unittest.mock import patch
from mnemo.persistence.export import export_obsidian


@pytest.fixture
def repo(tmp_path):
    mnemo_dir = tmp_path / ".mnemo"
    mnemo_dir.mkdir()
    with patch("mnemo.persistence.export.mnemo_path", return_value=mnemo_dir):
        yield tmp_path


def test_export_creates_markdown_files(repo):
    mnemo_dir = repo / ".mnemo"
    (mnemo_dir / "memory.json").write_text(json.dumps([
        {"id": "m1", "content": "Test memory", "category": "decision", "tags": ["arch"], "timestamp": "2024-01-01", "confidence": 0.9}
    ]))
    (mnemo_dir / "decisions.json").write_text("[]")
    output = repo / "export"
    with patch("mnemo.persistence.export.mnemo_path", return_value=mnemo_dir):
        result = export_obsidian(repo, output)
    assert (output / "memory-m1.md").exists()
    assert "Exported" in result


def test_yaml_frontmatter_format(repo):
    mnemo_dir = repo / ".mnemo"
    (mnemo_dir / "memory.json").write_text(json.dumps([
        {"id": "m1", "content": "Hello", "category": "pattern", "tags": ["test", "arch"], "timestamp": "2024-01-01", "confidence": 0.8}
    ]))
    (mnemo_dir / "decisions.json").write_text("[]")
    output = repo / "export"
    with patch("mnemo.persistence.export.mnemo_path", return_value=mnemo_dir):
        export_obsidian(repo, output)
    content = (output / "memory-m1.md").read_text()
    assert content.startswith("---\n")
    assert "category: pattern" in content
    assert "tags: [test, arch]" in content
    assert "confidence: 0.8" in content
    assert "Hello" in content


def test_moc_generation(repo):
    mnemo_dir = repo / ".mnemo"
    (mnemo_dir / "memory.json").write_text(json.dumps([
        {"id": "m1", "content": "A", "category": "general", "tags": [], "timestamp": "", "confidence": 1.0}
    ]))
    (mnemo_dir / "decisions.json").write_text(json.dumps([
        {"id": "d1", "decision": "Use Redis", "reasoning": "Fast", "timestamp": ""}
    ]))
    output = repo / "export"
    with patch("mnemo.persistence.export.mnemo_path", return_value=mnemo_dir):
        export_obsidian(repo, output)
    moc = (output / "MOC.md").read_text()
    assert "# Map of Content" in moc
    assert "[[memory-m1]]" in moc
    assert "[[decisions/decision-d1]]" in moc


def test_empty_memory_exports_gracefully(repo):
    mnemo_dir = repo / ".mnemo"
    # No memory.json or decisions.json
    output = repo / "export"
    with patch("mnemo.persistence.export.mnemo_path", return_value=mnemo_dir):
        result = export_obsidian(repo, output)
    assert (output / "MOC.md").exists()
    moc = (output / "MOC.md").read_text()
    assert "No entries" in moc
