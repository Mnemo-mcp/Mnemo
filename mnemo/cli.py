"""Mnemo CLI - persistent memory for AI coding chats."""

from __future__ import annotations

import sys
from pathlib import Path

# Support running as PyInstaller binary (no parent package)
if __package__ is None or __package__ == "":
    # Running as script — fix imports
    _root = Path(__file__).resolve().parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root.parent))
    __package__ = "mnemo"

import click

from .clients import CLIENT_CHOICES, DEFAULT_CLIENT


@click.group()
def cli():
    """Mnemo - persistent memory and repo map for AI coding assistants."""

    pass


@cli.command()
@click.option(
    "--client",
    "-c",
    default=DEFAULT_CLIENT,
    type=click.Choice(CLIENT_CHOICES),
    show_default=True,
    help="AI client to configure.",
)
@click.argument("path", default=".", type=click.Path(exists=True))
def init(path: str, client: str):
    """Initialize .mnemo/ in the current repo."""
    from .init import init as do_init

    result = do_init(Path(path).resolve(), client=client)
    click.echo(result)


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
def map(path: str):
    """Regenerate the repo map."""
    from .config import mnemo_path
    from .repo_map import save_repo_map

    repo_root = Path(path).resolve()
    if not mnemo_path(repo_root).exists():
        click.echo("Not initialized. Run `mnemo init` first.")
        return
    save_repo_map(repo_root)
    click.echo("Repo map updated.")


@cli.command()
@click.argument("content")
@click.option("--category", "-c", default="general")
@click.argument("path", default=".", type=click.Path(exists=True))
def remember(content: str, category: str, path: str):
    """Store a memory entry. Example: mnemo remember 'uses FastAPI'"""
    from .memory import add_memory

    entry = add_memory(Path(path).resolve(), content, category)
    click.echo(f"Remembered #{entry['id']}: {content}")


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
def recall(path: str):
    """Show all stored memory."""
    from .memory import recall as do_recall

    data = do_recall(Path(path).resolve())
    if not data:
        click.echo("No memory found. Run `mnemo init` first.")
        return
    click.echo(data)


@cli.command()
@click.option(
    "--client",
    "-c",
    default="all",
    type=click.Choice(CLIENT_CHOICES),
    show_default=True,
    help="AI client setup to inspect.",
)
@click.argument("path", default=".", type=click.Path(exists=True))
def doctor(path: str, client: str):
    """Diagnose Mnemo installation and client setup."""
    from .doctor import doctor as run_doctor

    click.echo(run_doctor(Path(path).resolve(), client=client))


@cli.command()
@click.option("--port", "-p", default=3333, help="Port to serve on")
@click.argument("path", default=".", type=click.Path(exists=True))
def serve(path: str, port: int):
    """Start the Mnemo UI dashboard. Run: mnemo serve"""
    from .serve import serve as start_server
    start_server(Path(path).resolve(), port=port)


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.confirmation_option(prompt="This will delete all Mnemo memory. Are you sure?")
def reset(path: str):
    """Wipe all Mnemo data and start fresh. Run: mnemo reset"""
    import shutil

    from .config import mnemo_path
    from .clients import CLIENTS, context_path

    repo_root = Path(path).resolve()
    base = mnemo_path(repo_root)

    if not base.exists():
        click.echo("Nothing to reset - .mnemo/ not found.")
        return

    # Remove .mnemo/ data
    click.echo("⏳ Removing .mnemo/ data...")
    shutil.rmtree(base)
    click.echo("  ✓ .mnemo/ deleted")

    # Remove client context files
    click.echo("⏳ Removing context files...")
    for target in CLIENTS.values():
        ctx = context_path(repo_root, target)
        if ctx and ctx.exists():
            ctx.unlink()
            click.echo(f"  ✓ Removed {ctx.relative_to(repo_root)}")

    # Remove generated Kiro files
    click.echo("⏳ Removing generated Kiro/agent files...")
    kiro_dirs = [
        repo_root / ".kiro" / "hooks",
        repo_root / ".kiro" / "agents",
        repo_root / ".kiro" / "skills",
    ]
    for d in kiro_dirs:
        if d.exists():
            shutil.rmtree(d)
            click.echo(f"  ✓ Removed {d.relative_to(repo_root)}/")

    kiro_mcp = repo_root / ".kiro" / "settings" / "mcp.json"
    if kiro_mcp.exists():
        kiro_mcp.unlink()
        click.echo(f"  ✓ Removed {kiro_mcp.relative_to(repo_root)}")

    # Remove .kiro/ dir itself if empty
    kiro_dir = repo_root / ".kiro"
    if kiro_dir.exists() and not any(kiro_dir.rglob("*")):
        shutil.rmtree(kiro_dir)
        click.echo("  ✓ Removed empty .kiro/")

    # Remove Claude Code hooks
    claude_hooks = repo_root / ".claude" / "hooks"
    if claude_hooks.exists():
        shutil.rmtree(claude_hooks)
        click.echo(f"  ✓ Removed {claude_hooks.relative_to(repo_root)}/")
    claude_guide = repo_root / ".claude" / "mnemo-guide.md"
    if claude_guide.exists():
        claude_guide.unlink()
        click.echo(f"  ✓ Removed {claude_guide.relative_to(repo_root)}")

    click.echo("\n✅ Reset complete. Run `mnemo init` to start fresh.")


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
def status(path: str):
    """Quick check: is Mnemo initialized and MCP server responding?"""
    from .config import mnemo_path
    from .clients import find_mnemo_mcp_command
    from .doctor import _check_mcp_alive

    repo_root = Path(path).resolve()
    base = mnemo_path(repo_root)

    if not base.exists():
        click.echo("❌ Not initialized. Run: mnemo init")
        return

    command = find_mnemo_mcp_command()
    alive = _check_mcp_alive(command)

    if alive:
        click.echo("✅ Mnemo active — MCP server responding")
    else:
        click.echo("⚠️  Mnemo initialized but MCP server not responding — restart your IDE")


@cli.command()
@click.argument("target", required=False)
@click.option("--discover", "-d", type=click.Path(exists=True), help="Auto-discover all repos under a directory.")
@click.option("--init", "auto_init", is_flag=True, help="Auto-initialize discovered repos that haven't been set up.")
@click.argument("path", default=".", type=click.Path(exists=True))
def link(target: str | None, discover: str | None, auto_init: bool, path: str):
    """Link a sibling repo for cross-repo queries. Use --discover to auto-find repos."""
    from .workspace import link_repo, discover_repos

    repo_root = Path(path).resolve()
    if discover:
        result = discover_repos(repo_root, Path(discover), auto_init=auto_init)
    elif target:
        result = link_repo(repo_root, Path(target))
    else:
        click.echo("Provide a repo path or use --discover <dir>")
        return
    click.echo(result)


@cli.command()
@click.argument("name")
@click.argument("path", default=".", type=click.Path(exists=True))
def unlink(name: str, path: str):
    """Remove a linked repo."""
    from .workspace import unlink_repo

    click.echo(unlink_repo(Path(path).resolve(), name))


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
def links(path: str):
    """Show all linked repos and their status."""
    from .workspace import format_links

    click.echo(format_links(Path(path).resolve()))


@cli.command()
def update():
    """Update Mnemo to the latest version."""
    import platform
    import shutil
    import stat
    import tempfile
    import urllib.request
    import json as json_mod

    from . import __version__

    REPO = "Mnemo-mcp/Mnemo"
    API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"

    # Fetch latest release info
    click.echo("Checking for updates...")
    try:
        with urllib.request.urlopen(API_URL, timeout=10) as resp:  # nosec B310
            release = json_mod.loads(resp.read())
    except Exception as e:
        click.echo(f"Failed to check for updates: {e}")
        return

    latest = release.get("tag_name", "").lstrip("v")
    if not latest:
        click.echo("Could not determine latest version.")
        return

    if latest == __version__:
        click.echo(f"Already on latest version ({__version__}).")
        return

    click.echo(f"Current: {__version__} → Latest: {latest}")

    # Determine which binary to download
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "darwin":
        asset_name = "mnemo-darwin-arm64" if "arm" in machine else "mnemo-darwin-x64"
    elif system == "linux":
        asset_name = "mnemo-linux-x64"
    elif system == "windows":
        asset_name = "mnemo-win-x64.exe"
    else:
        click.echo(f"Unsupported platform: {system}. Use pip install --upgrade mnemo instead.")
        return

    # Find download URL
    download_url = None
    for asset in release.get("assets", []):
        if asset["name"] == asset_name:
            download_url = asset["browser_download_url"]
            break

    if not download_url:
        click.echo(f"Binary '{asset_name}' not found in release. Use pip install --upgrade mnemo instead.")
        return

    # Download
    click.echo(f"Downloading {asset_name}...")
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".tmp")
        urllib.request.urlretrieve(download_url, tmp.name)  # nosec B310
    except Exception as e:
        click.echo(f"Download failed: {e}")
        return

    # Replace current binary
    current_exe = shutil.which("mnemo")
    if not current_exe:
        current_exe = sys.executable if getattr(sys, "frozen", False) else None

    if not current_exe or not getattr(sys, "frozen", False):
        # Not running as binary — suggest pip
        import os
        os.unlink(tmp.name)
        click.echo("Not running as standalone binary. Use: pip install --upgrade mnemo")
        return

    try:
        target = Path(current_exe)
        # Replace in place
        shutil.move(tmp.name, str(target))
        target.chmod(target.stat().st_mode | stat.S_IEXEC)
        click.echo(f"✅ Updated to v{latest}")
    except PermissionError:
        click.echo("Permission denied. Try: sudo mnemo update")
    except Exception as e:
        click.echo(f"Failed to replace binary: {e}")


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
def commit(path: str):
    """Generate a commit message from staged changes + memory context."""
    from .commit_gen import generate_commit_message

    result = generate_commit_message(Path(path).resolve())
    click.echo(result)


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
def pr(path: str):
    """Generate a PR description from branch diff + task context + memory."""
    from .pr_gen import generate_pr_description

    result = generate_pr_description(Path(path).resolve())
    click.echo(result)


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
def velocity(path: str):
    """Show development velocity metrics from git history."""
    from .velocity import calculate_velocity

    click.echo(calculate_velocity(Path(path).resolve()))


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
def check(path: str):
    """Run pre-commit validations (security scan on staged files)."""
    from .hooks import run_check

    result = run_check(Path(path).resolve())
    click.echo(result)


@cli.group()
def hooks():
    """Manage git hooks."""
    pass


@hooks.command()
@click.argument("path", default=".", type=click.Path(exists=True))
def install(path: str):
    """Install Mnemo pre-commit hook."""
    from .hooks import install_hooks

    click.echo(install_hooks(Path(path).resolve()))


cli.add_command(hooks)


@cli.command("mcp-server", hidden=True)
def mcp_server():
    """Run the MCP server over stdio (used by AI clients)."""
    from .mcp_server import run_stdio
    run_stdio()


@cli.command("tool", context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.argument("tool_name")
@click.pass_context
def tool(ctx, tool_name: str):
    """Run any Mnemo tool by name (CLI gateway for agents without MCP).

    Examples:
        mnemo tool recall
        mnemo tool lookup --query AuthService
        mnemo tool graph --action stats
        mnemo tool remember --content "uses Redis for caching"
        mnemo tool search_memory --query "auth" --deep true
    """
    import json as json_mod
    from .mcp_server import handle_tool_call

    # Normalize: allow both "recall" and "mnemo_recall"
    if not tool_name.startswith("mnemo_"):
        tool_name = f"mnemo_{tool_name}"

    # Parse --key value pairs from extra args
    args = {}
    extra = ctx.args
    i = 0
    while i < len(extra):
        token = extra[i]
        if token.startswith("--"):
            key = token.lstrip("-")
            if i + 1 < len(extra) and not extra[i + 1].startswith("--"):
                val = extra[i + 1]
                # Try to parse as JSON for complex types (arrays, objects, booleans)
                try:
                    val = json_mod.loads(val)
                except (json_mod.JSONDecodeError, ValueError):
                    pass
                args[key] = val
                i += 2
            else:
                args[key] = True
                i += 1
        else:
            i += 1

    result = handle_tool_call(tool_name, args)
    # handle_tool_call returns a dict with content
    content = result.get("content", [])
    for block in content:
        if block.get("type") == "text":
            click.echo(block["text"])


@cli.command("tools")
def tools_list():
    """List all available Mnemo tools."""
    from .tool_registry import all_tools

    for t in all_tools():
        name = t["name"].replace("mnemo_", "")
        click.echo(f"  {name:25s} {t['description'][:80]}")
    click.echo("\nUsage: mnemo tool <name> [--arg value ...]")
    click.echo("Example: mnemo tool lookup --query AuthService")


@cli.command()
@click.option("--port", "-p", default=7890, help="Port to serve on.")
@click.option("--no-open", is_flag=True, help="Don't auto-open browser.")
@click.argument("path", default=".", type=click.Path(exists=True))
def ui(path: str, port: int, no_open: bool):
    """Open the Mnemo dashboard in your browser."""
    from .config import mnemo_path
    from .ui import start_server

    repo_root = Path(path).resolve()
    if not mnemo_path(repo_root).exists():
        click.echo("Not initialized. Run `mnemo init` first.")
        return
    start_server(repo_root, port=port, open_browser=not no_open)


if __name__ == "__main__":
    cli()
