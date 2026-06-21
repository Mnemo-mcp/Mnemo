"""Binary discovery for mnemo-mcp and mnemo CLI."""

from __future__ import annotations

import shutil
from pathlib import Path


def find_mnemo_mcp(repo_root: Path | None = None) -> str:
    """Find the mnemo-mcp binary path."""
    mnemo_mcp = shutil.which("mnemo-mcp")
    if not mnemo_mcp:
        candidates = [
            Path.home() / ".local" / "bin" / "mnemo-mcp",
            Path.home() / "Library" / "Python" / "3.12" / "bin" / "mnemo-mcp",
            Path.home() / "Library" / "Python" / "3.11" / "bin" / "mnemo-mcp",
            Path.home() / "Library" / "Python" / "3.13" / "bin" / "mnemo-mcp",
            Path("/opt/homebrew/bin/mnemo-mcp"),
            Path("/usr/local/bin/mnemo-mcp"),
            Path.home() / "bin" / "mnemo-mcp",
            Path.home() / ".mnemo" / "bin" / "mnemo-mcp",
        ]
        vscode_ext_dir = Path.home() / ".vscode" / "extensions"
        if vscode_ext_dir.exists():
            for ext_dir in vscode_ext_dir.glob("mnemo*"):
                candidates.append(ext_dir / "bin" / "mnemo-mcp")
                candidates.append(ext_dir / "mnemo-mcp")
        vscode_server_dir = Path.home() / ".vscode-server" / "extensions"
        if vscode_server_dir.exists():
            for ext_dir in vscode_server_dir.glob("mnemo*"):
                candidates.append(ext_dir / "bin" / "mnemo-mcp")

        for candidate in candidates:
            if candidate.exists():
                mnemo_mcp = str(candidate)
                break

    if not mnemo_mcp:
        mnemo_mcp = "mnemo-mcp"  # Fallback: assume it's on PATH at runtime

    return mnemo_mcp


def find_mnemo_cli() -> str:
    """Find the mnemo CLI binary path."""
    return shutil.which("mnemo") or "mnemo"
