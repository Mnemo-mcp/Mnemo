import json
from pathlib import Path

import pytest

from mnemo.clients import ClientTarget, resolve_clients, setup_mcp_config


def test_resolve_clients_rejects_unknown_client():
    with pytest.raises(ValueError, match="Unknown client"):
        resolve_clients("not-a-client")


def test_setup_mcp_config_adds_mnemo_server(tmp_path: Path):
    target = ClientTarget(
        key="test",
        display_name="Test Client",
        mcp_config_path=tmp_path / "mcp.json",
        context_file="TEST.md",
        context_label="instructions",
    )

    changed = setup_mcp_config(target, command="mnemo-mcp")

    assert changed is True
    config = json.loads(target.mcp_config_path.read_text(encoding="utf-8"))
    assert config["mcpServers"]["mnemo"] == {
        "command": "mnemo-mcp",
        "args": [],
        "env": {},
    }


def test_setup_mcp_config_is_idempotent(tmp_path: Path):
    target = ClientTarget(
        key="test",
        display_name="Test Client",
        mcp_config_path=tmp_path / "mcp.json",
        context_file="TEST.md",
        context_label="instructions",
    )

    assert setup_mcp_config(target, command="mnemo-mcp") is True
    assert setup_mcp_config(target, command="mnemo-mcp") is False
