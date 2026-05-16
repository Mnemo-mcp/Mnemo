"""Mnemo doctor — diagnose installation and MCP connectivity."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .config import mnemo_path


def doctor(repo_root: Path, client: str = "kiro") -> str:
    """Run diagnostics on a Mnemo installation."""
    lines = ["# Mnemo Doctor\n"]
    base = mnemo_path(repo_root)

    # Check .mnemo/ exists
    if not base.exists():
        lines.append("❌ .mnemo/ not found — run `mnemo init`")
        return "\n".join(lines)
    lines.append("✅ .mnemo/ directory exists")

    # Check key files
    for f in ("memory.json", "context.json", "hashes.json"):
        if (base / f).exists():
            lines.append(f"✅ {f}")
        else:
            lines.append(f"⚠️  {f} missing")

    # Check graph
    graph_path = base / "graph.lbug"
    if graph_path.exists():
        size_mb = graph_path.stat().st_size / 1024 / 1024
        lines.append(f"✅ graph.lbug ({size_mb:.1f} MB)")
    else:
        lines.append("❌ graph.lbug missing — run `mnemo init`")

    # Check vector index
    vec_path = base / "vectors_memory.npy"
    if vec_path.exists():
        lines.append("✅ Vector index (semantic search ready)")
    else:
        lines.append("⚠️  No vector index — search will be keyword-only until memories are stored")

    # Check MCP
    command = _find_mnemo_command()
    if command:
        lines.append(f"✅ mnemo binary: {command}")
        if _check_mcp_alive(command):
            lines.append("✅ MCP server responding")
        else:
            lines.append("⚠️  MCP server not responding (normal if IDE not running)")
    else:
        lines.append("❌ mnemo binary not found in PATH")

    # Check client config
    lines.append(f"\n## Client: {client}")
    client_configs = {
        "kiro": repo_root / ".kiro" / "settings" / "mcp.json",
        "cursor": Path.home() / ".cursor" / "mcp.json",
        "claude-code": Path.home() / ".claude" / "mcp.json",
    }
    cfg = client_configs.get(client)
    if cfg and cfg.exists():
        lines.append(f"✅ MCP config: {cfg}")
    elif cfg:
        lines.append(f"❌ MCP config not found: {cfg}")

    return "\n".join(lines)


def _find_mnemo_command() -> str | None:
    """Find the mnemo-mcp binary."""
    try:
        r = subprocess.run(["which", "mnemo-mcp"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return None


def _check_mcp_alive(command: str | None) -> bool:
    """Check if the MCP server responds to a basic request."""
    if not command:
        return False
    try:
        import json
        req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        r = subprocess.run(
            [command], input=req + "\n", capture_output=True, text=True, timeout=5
        )
        return "protocolVersion" in r.stdout
    except Exception:
        return False
