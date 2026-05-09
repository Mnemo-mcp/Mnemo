import json
from pathlib import Path

import mnemo.clients as clients
import mnemo.doctor as doctor_module
from mnemo.clients import ClientTarget


def test_doctor_reports_initialized_client_setup(monkeypatch, tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".mnemo").mkdir()
    (repo_root / ".mnemo" / "context.json").write_text("{}", encoding="utf-8")
    (repo_root / ".mnemo" / "memory.json").write_text("[]", encoding="utf-8")
    (repo_root / ".mnemo" / "decisions.json").write_text("[]", encoding="utf-8")
    (repo_root / ".mnemo" / "hashes.json").write_text("{}", encoding="utf-8")
    (repo_root / "TEST.md").write_text("mnemo_recall", encoding="utf-8")

    mcp_config = tmp_path / "home" / "mcp.json"
    mcp_config.parent.mkdir(parents=True)
    mcp_config.write_text(
        json.dumps({"mcpServers": {"mnemo": {"command": "mnemo-mcp"}}}),
        encoding="utf-8",
    )
    target = ClientTarget("test", "Test Client", mcp_config, "TEST.md", "instructions")

    monkeypatch.setattr(clients, "CLIENTS", {"test": target})
    monkeypatch.setattr(doctor_module, "find_mnemo_mcp_command", lambda: "mnemo-mcp")

    output = doctor_module.doctor(repo_root, client="test")

    assert "[OK] Repository initialized" in output
    assert "[OK] Test Client context" in output
    assert "[OK] Test Client MCP config" in output


def test_doctor_tells_user_to_init_uninitialized_repo(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    output = doctor_module.doctor(repo_root, client="generic")

    assert "[WARN] Repository initialized" in output
    assert "Run `mnemo init`" in output
