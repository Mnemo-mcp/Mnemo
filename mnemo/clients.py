"""AI client configuration targets for Mnemo."""

from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ClientTarget:
    """Configuration and context-file locations for an MCP client."""

    key: str
    display_name: str
    mcp_config_path: Path | None
    context_file: str | None
    context_label: str


CLIENTS: dict[str, ClientTarget] = {
    "amazonq": ClientTarget(
        key="amazonq",
        display_name="Amazon Q",
        mcp_config_path=Path.home() / ".aws" / "amazonq" / "mcp.json",
        context_file=".amazonq/rules/mnemo.md",
        context_label="rule",
    ),
    "cursor": ClientTarget(
        key="cursor",
        display_name="Cursor",
        mcp_config_path=Path.home() / ".cursor" / "mcp.json",
        context_file=".cursorrules",
        context_label="rules file",
    ),
    "claude-code": ClientTarget(
        key="claude-code",
        display_name="Claude Code",
        mcp_config_path=Path.home() / ".claude" / "mcp.json",
        context_file="CLAUDE.md",
        context_label="project instructions",
    ),
    "kiro": ClientTarget(
        key="kiro",
        display_name="Kiro",
        mcp_config_path=Path.home() / ".kiro" / "mcp.json",
        context_file=".kiro/rules/mnemo.md",
        context_label="rule",
    ),
    "copilot": ClientTarget(
        key="copilot",
        display_name="GitHub Copilot",
        mcp_config_path=Path.home() / ".config" / "github-copilot" / "mcp.json",
        context_file=".github/copilot-instructions.md",
        context_label="instructions",
    ),
    "generic": ClientTarget(
        key="generic",
        display_name="Generic MCP Client",
        mcp_config_path=None,
        context_file="MNEMO.md",
        context_label="instructions",
    ),
}

DEFAULT_CLIENT = "amazonq"
CLIENT_CHOICES = tuple(CLIENTS.keys()) + ("all",)


def resolve_clients(selection: str) -> list[ClientTarget]:
    """Resolve a CLI client selection into concrete client targets."""
    normalized = selection.lower().strip()
    if normalized == "all":
        return list(CLIENTS.values())
    try:
        return [CLIENTS[normalized]]
    except KeyError as exc:
        valid = ", ".join(CLIENT_CHOICES)
        raise ValueError(f"Unknown client '{selection}'. Choose one of: {valid}") from exc


def find_mnemo_mcp_command() -> str:
    """Find the installed mnemo-mcp executable, falling back to PATH lookup by name."""
    mnemo_bin = shutil.which("mnemo-mcp")
    if mnemo_bin:
        return mnemo_bin

    executable_name = "mnemo-mcp.exe" if sys.platform.startswith("win") else "mnemo-mcp"
    candidates = [
        Path(sys.prefix) / "Scripts" / executable_name,
        Path(sys.prefix) / "bin" / executable_name,
        Path.home() / ".local" / "bin" / executable_name,
        Path.home() / "Library" / "Python" / "3.12" / "bin" / executable_name,
        Path.home() / "Library" / "Python" / "3.11" / "bin" / executable_name,
        Path.home() / "AppData" / "Roaming" / "Python" / "Python312" / "Scripts" / executable_name,
        Path.home() / "AppData" / "Roaming" / "Python" / "Python311" / "Scripts" / executable_name,
        Path.home() / "AppData" / "Roaming" / "Python" / "Python310" / "Scripts" / executable_name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return "mnemo-mcp"


def setup_mcp_config(target: ClientTarget, command: str | None = None) -> bool:
    """Register Mnemo in a client's MCP config.

    Returns True when the config file changed.
    """
    if target.mcp_config_path is None:
        return False

    config_path = target.mcp_config_path
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            config = {}

    config.setdefault("mcpServers", {})
    server = {
        "command": command or find_mnemo_mcp_command(),
        "args": [],
        "env": {},
    }

    if config["mcpServers"].get("mnemo") == server:
        return False

    config["mcpServers"]["mnemo"] = server
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return True


def context_path(repo_root: Path, target: ClientTarget) -> Path | None:
    """Return the repo-local context file path for a client."""
    if not target.context_file:
        return None
    return repo_root / target.context_file
