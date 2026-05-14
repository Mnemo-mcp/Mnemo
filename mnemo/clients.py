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
    local_mcp_config: str | None = None  # repo-relative path for project-local MCP config


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
        mcp_config_path=None,
        context_file=".kiro/rules/mnemo.md",
        context_label="rule",
        local_mcp_config=".kiro/settings/mcp.json",
    ),
    "copilot": ClientTarget(
        key="copilot",
        display_name="GitHub Copilot",
        mcp_config_path=Path.home() / ".config" / "github-copilot" / "mcp.json",
        context_file=".github/copilot-instructions.md",
        context_label="instructions",
    ),
    "gemini-cli": ClientTarget(
        key="gemini-cli",
        display_name="Gemini CLI",
        mcp_config_path=Path.home() / ".gemini" / "mcp.json",
        context_file=".gemini/MNEMO.md",
        context_label="instructions",
    ),
    "windsurf": ClientTarget(
        key="windsurf",
        display_name="Windsurf",
        mcp_config_path=Path.home() / ".windsurf" / "mcp.json",
        context_file=".windsurf/MNEMO.md",
        context_label="instructions",
    ),
    "cline": ClientTarget(
        key="cline",
        display_name="Cline",
        mcp_config_path=Path.home() / ".cline" / "mcp.json",
        context_file=".cline/MNEMO.md",
        context_label="instructions",
    ),
    "roo-code": ClientTarget(
        key="roo-code",
        display_name="Roo Code",
        mcp_config_path=Path.home() / ".roo-code" / "mcp.json",
        context_file=".roo-code/MNEMO.md",
        context_label="instructions",
    ),
    "opencode": ClientTarget(
        key="opencode",
        display_name="OpenCode",
        mcp_config_path=Path.home() / ".opencode" / "mcp.json",
        context_file=".opencode/MNEMO.md",
        context_label="instructions",
    ),
    "goose": ClientTarget(
        key="goose",
        display_name="Goose",
        mcp_config_path=Path.home() / ".goose" / "mcp.json",
        context_file=".goose/MNEMO.md",
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
        return [v for v in CLIENTS.values() if v.key != "generic"]
    # Alias: gemini → gemini-cli
    if normalized == "gemini":
        normalized = "gemini-cli"
    try:
        return [CLIENTS[normalized]]
    except KeyError as exc:
        valid = ", ".join(CLIENT_CHOICES)
        raise ValueError(f"Unknown client '{selection}'. Choose one of: {valid}") from exc


def find_mnemo_mcp_command() -> str:
    """Find the installed mnemo-mcp executable, falling back to PATH lookup by name."""
    if getattr(sys, "frozen", False):
        # Running as PyInstaller binary — use self with mcp-server subcommand
        return str(Path(sys.executable))

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

    # Fallback: check if single binary `mnemo` exists (supports `mnemo mcp-server`)
    mnemo_cli = shutil.which("mnemo")
    if mnemo_cli:
        return mnemo_cli

    return "mnemo-mcp"


def setup_mcp_config(target: ClientTarget, command: str | None = None, repo_root: Path | None = None) -> bool:
    """Register Mnemo in a client's MCP config.

    Returns True when the config file changed.
    """
    if target.local_mcp_config and repo_root:
        config_path = repo_root / target.local_mcp_config
    elif target.mcp_config_path:
        config_path = target.mcp_config_path
    else:
        return False
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            config = {}

    config.setdefault("mcpServers", {})

    cmd = command or find_mnemo_mcp_command()
    # If the command is the single binary (not mnemo-mcp), add mcp-server arg
    args: list[str] = []
    if not cmd.endswith("mnemo-mcp") and not cmd.endswith("mnemo-mcp.exe"):
        args = ["mcp-server"]

    server = {
        "command": cmd,
        "args": args,
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
