import json
from pathlib import Path

from mnemo.memory import add_decision, add_memory, recall, save_context


def test_memory_context_and_decisions_keep_existing_file_shapes(tmp_path: Path):
    add_memory(tmp_path, "Use handlers for provider-specific behavior", "pattern")
    add_decision(tmp_path, "Keep JSON local storage", "Local dev should stay simple")
    save_context(tmp_path, {"repo_root": str(tmp_path), "initialized": True})

    base = tmp_path / ".mnemo"

    memory = json.loads((base / "memory.json").read_text(encoding="utf-8"))
    assert memory[0]["content"] == "Use handlers for provider-specific behavior"

    decisions = json.loads((base / "decisions.json").read_text(encoding="utf-8"))
    assert decisions[0]["decision"] == "Keep JSON local storage"

    context = json.loads((base / "context.json").read_text(encoding="utf-8"))
    assert context["repo_root"] == str(tmp_path)
    assert context["initialized"] is True
    assert "last_updated" in context


def test_recall_reads_memory_collections_through_storage(monkeypatch, tmp_path: Path):
    add_memory(tmp_path, "Prefer small shippable increments")
    add_decision(tmp_path, "Support multiple AI clients")
    save_context(tmp_path, {"repo_root": str(tmp_path)})
    (tmp_path / ".mnemo" / "tree.md").write_text("**src/**\n  app.py", encoding="utf-8")

    output = recall(tmp_path)

    assert "# Project Context" in output
    assert "Support multiple AI clients" in output
    assert "Prefer small shippable increments" in output
    assert "**src/**" in output
