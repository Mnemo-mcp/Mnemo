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

    # Check hook paths (Kiro)
    agent_json = repo_root / ".kiro" / "agents" / "mnemo-enhanced.json"
    if agent_json.exists():
        import json
        try:
            agent_config = json.loads(agent_json.read_text())
            hooks = agent_config.get("hooks", {})
            stale_hooks = []
            for hook_type, hook_list in hooks.items():
                for hook in hook_list:
                    cmd = hook.get("command", "")
                    if cmd.startswith("/") and not Path(cmd).exists():
                        stale_hooks.append((hook_type, cmd))
                    elif cmd.startswith("/"):
                        # Absolute but exists — warn that it won't survive repo moves
                        stale_hooks.append((hook_type, f"{cmd} (absolute path — will break if repo moves)"))
            if stale_hooks:
                lines.append(f"\n❌ STALE HOOK PATHS ({len(stale_hooks)} broken):")
                for hook_type, path in stale_hooks:
                    lines.append(f"   {hook_type}: {path}")
                lines.append("   Fix: run `mnemo init --client kiro` to regenerate with relative paths")
                # Auto-fix: rewrite with relative paths
                _auto_fix_hook_paths(agent_json, repo_root)
                lines.append("   ✅ AUTO-FIXED: rewrote hooks to use relative paths")
            else:
                lines.append("✅ Hook paths valid")
        except (json.JSONDecodeError, KeyError):
            lines.append("⚠️  Could not parse mnemo-enhanced.json")

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


def _auto_fix_hook_paths(agent_json: Path, repo_root: Path) -> None:
    """Rewrite absolute hook paths to relative paths."""
    import re
    content = agent_json.read_text()
    # Replace any absolute path ending in .kiro/hooks/*.sh with relative
    content = re.sub(
        r'"command":\s*"/[^"]*\.kiro/hooks/([^"]+)"',
        r'"command": ".kiro/hooks/\1"',
        content,
    )
    agent_json.write_text(content)


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
