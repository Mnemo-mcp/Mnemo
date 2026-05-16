from pathlib import Path

import mnemo.clients as clients
import mnemo.init as init_module
from mnemo.clients import ClientTarget


def test_init_configures_selected_client(monkeypatch, tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    home = tmp_path / "home"

    target = ClientTarget(
        key="claude-code",
        display_name="Claude Code",
        mcp_config_path=home / ".claude" / "mcp.json",
        context_file="CLAUDE.md",
        context_label="project instructions",
    )
    test_clients = {target.key: target}

    monkeypatch.setattr(clients, "CLIENTS", test_clients)
    monkeypatch.setattr(init_module, "CLIENTS", test_clients)
    monkeypatch.setattr("mnemo.engine.pipeline.run_pipeline", lambda root, force=False: type("S", (), {"files_scanned": 0, "nodes_created": 0, "edges_created": 0, "total_ms": 1})())
    monkeypatch.setattr("mnemo.knowledge.init_knowledge", lambda root: root / ".mnemo" / "knowledge")
    monkeypatch.setattr("mnemo.memory.recall", lambda root: "# Project Context\n")

    result = init_module.init(repo_root, client="claude-code")

    assert (repo_root / ".mnemo").exists()
    assert (repo_root / ".gitignore").read_text(encoding="utf-8") == ".mnemo/\n"
    assert (repo_root / "CLAUDE.md").exists()
    assert "mnemo_recall" in (repo_root / "CLAUDE.md").read_text(encoding="utf-8")
    assert target.mcp_config_path.exists()
    assert "Claude Code MCP configured" in result


def test_init_all_configures_every_client(monkeypatch, tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    first = ClientTarget(
        key="amazonq",
        display_name="Amazon Q",
        mcp_config_path=tmp_path / "home" / ".aws" / "amazonq" / "mcp.json",
        context_file=".amazonq/rules/mnemo.md",
        context_label="rule",
    )
    second = ClientTarget(
        key="cursor",
        display_name="Cursor",
        mcp_config_path=tmp_path / "home" / ".cursor" / "mcp.json",
        context_file=".cursorrules",
        context_label="rules file",
    )
    test_clients = {first.key: first, second.key: second}

    monkeypatch.setattr(clients, "CLIENTS", test_clients)
    monkeypatch.setattr(init_module, "CLIENTS", test_clients)
    monkeypatch.setattr("mnemo.engine.pipeline.run_pipeline", lambda root, force=False: type("S", (), {"files_scanned": 0, "nodes_created": 0, "edges_created": 0, "total_ms": 1})())
    monkeypatch.setattr("mnemo.knowledge.init_knowledge", lambda root: root / ".mnemo" / "knowledge")
    monkeypatch.setattr("mnemo.memory.recall", lambda root: "# Project Context\n")

    init_module.init(repo_root, client="all")

    assert (repo_root / ".amazonq" / "rules" / "mnemo.md").exists()
    assert (repo_root / ".cursorrules").exists()
    assert first.mcp_config_path.exists()
    assert second.mcp_config_path.exists()
