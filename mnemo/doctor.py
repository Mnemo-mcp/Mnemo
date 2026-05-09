"""Installation and setup diagnostics for Mnemo."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from importlib.metadata import PackageNotFoundError, version

from .clients import DEFAULT_CLIENT, ClientTarget, context_path, find_mnemo_mcp_command, resolve_clients
from .config import mnemo_path


def _status(ok: bool) -> str:
    return "OK" if ok else "WARN"


def _check_mcp_config(target: ClientTarget) -> tuple[bool, str]:
    if target.mcp_config_path is None:
        return True, "manual MCP config required"
    if not target.mcp_config_path.exists():
        return False, f"missing {target.mcp_config_path}"
    try:
        config = json.loads(target.mcp_config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False, f"invalid JSON in {target.mcp_config_path}"
    if "mnemo" not in config.get("mcpServers", {}):
        return False, f"mnemo server not registered in {target.mcp_config_path}"
    return True, str(target.mcp_config_path)


def _check_context_file(repo_root: Path, target: ClientTarget) -> tuple[bool, str]:
    path = context_path(repo_root, target)
    if path is None:
        return True, "no context file required"
    if path.exists():
        return True, str(path.relative_to(repo_root))
    return False, f"missing {path.relative_to(repo_root)}"


def doctor(repo_root: Path, client: str = DEFAULT_CLIENT) -> str:
    """Return a human-readable setup diagnostic report."""
    targets = resolve_clients(client)
    lines = ["# Mnemo Doctor", ""]

    python_ok = sys.version_info >= (3, 10)
    lines.append(f"[{_status(python_ok)}] Python: {sys.version.split()[0]} (requires 3.10+)")

    try:
        package_version = version("mnemo")
        lines.append(f"[OK] Mnemo package: {package_version}")
    except PackageNotFoundError:
        lines.append("[WARN] Mnemo package: not installed as a package")

    command = find_mnemo_mcp_command()
    command_ok = command != "mnemo-mcp"
    lines.append(f"[{_status(command_ok)}] mnemo-mcp command: {command}")

    base = mnemo_path(repo_root)
    initialized = base.exists()
    lines.append(f"[{_status(initialized)}] Repository initialized: {base}")

    if initialized:
        for filename in ("context.json", "memory.json", "decisions.json", "hashes.json"):
            path = base / filename
            exists = path.exists()
            lines.append(f"[{_status(exists)}] {filename}: {path}")

    lines.append("")
    lines.append("## Client Setup")
    for target in targets:
        context_ok, context_message = _check_context_file(repo_root, target)
        config_ok, config_message = _check_mcp_config(target)
        lines.append(f"[{_status(context_ok)}] {target.display_name} context: {context_message}")
        lines.append(f"[{_status(config_ok)}] {target.display_name} MCP config: {config_message}")

    if not initialized:
        lines.append("")
        lines.append("Run `mnemo init` in this repository.")
    else:
        missing_clients = [
            target.display_name
            for target in targets
            if not _check_context_file(repo_root, target)[0] or not _check_mcp_config(target)[0]
        ]
        if missing_clients:
            lines.append("")
            lines.append(f"Run `mnemo init --client {client}` to repair missing client setup.")

    return "\n".join(lines)
