"""Mnemo CLI - persistent memory for AI coding chats."""

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
@click.argument("path", default=".", type=click.Path(exists=True))
@click.confirmation_option(prompt="This will delete all Mnemo memory. Are you sure?")
def reset(path: str):
    """Wipe all Mnemo data and start fresh. Run: mnemo reset"""
    import shutil

    from .config import mnemo_path
    from .clients import CLIENTS, context_path

    repo_root = Path(path).resolve()
    base = mnemo_path(repo_root)

    # Remove .mnemo/ data
    if base.exists():
        shutil.rmtree(base)
        click.echo(".mnemo/ deleted.")
    else:
        click.echo("Nothing to reset - .mnemo/ not found.")
        return

    # Remove client context files
    for target in CLIENTS.values():
        ctx = context_path(repo_root, target)
        if ctx and ctx.exists():
            ctx.unlink()
            click.echo(f"Removed {ctx.relative_to(repo_root)}")

    click.echo("Run `mnemo init` to start fresh.")


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
        with urllib.request.urlopen(API_URL, timeout=10) as resp:
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
        urllib.request.urlretrieve(download_url, tmp.name)
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
        click.echo(f"Permission denied. Try: sudo mnemo update")
    except Exception as e:
        click.echo(f"Failed to replace binary: {e}")


@cli.command("mcp-server", hidden=True)
def mcp_server():
    """Run the MCP server over stdio (used by AI clients)."""
    from .mcp_server import run_stdio
    run_stdio()


if __name__ == "__main__":
    cli()
