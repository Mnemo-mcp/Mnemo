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


def _check_for_update_quietly():
    """Check PyPI for newer version, at most once per day. Non-blocking."""
    import json as _json
    import time as _time

    from . import __version__

    cache = Path.home() / ".mnemo_update_check"
    now = _time.time()

    # Only check once per 24h
    if cache.exists():
        try:
            data = _json.loads(cache.read_text())
            if now - data.get("ts", 0) < 86400:
                if data.get("latest") and data["latest"] != __version__:
                    click.echo(
                        f"\n  ⬆  Mnemo {data['latest']} available (you have {__version__}). "
                        f"Run: mnemo update\n",
                        err=True,
                    )
                return
        except Exception:
            pass

    # Background check — don't slow down CLI
    try:
        import urllib.request
        url = "https://pypi.org/pypi/mnemo-dev/json"
        with urllib.request.urlopen(url, timeout=3) as resp:  # nosec B310
            latest = _json.loads(resp.read()).get("info", {}).get("version", "")
        cache.write_text(_json.dumps({"ts": now, "latest": latest}))
        if latest and latest != __version__:
            click.echo(
                f"\n  ⬆  Mnemo {latest} available (you have {__version__}). "
                f"Run: mnemo update\n",
                err=True,
            )
    except Exception:
        # Network error — silently skip
        pass


@click.group()
def cli():
    """Mnemo - persistent memory and repo map for AI coding assistants."""
    _check_for_update_quietly()


@cli.command()
@click.option(
    "--client",
    "-c",
    default=None,
    type=click.Choice(CLIENT_CHOICES),
    help="AI client to configure (required).",
)
@click.argument("path", default=".", type=click.Path(exists=True))
def init(path: str, client: str | None):
    """Initialize .mnemo/ in the current repo."""
    if client is None:
        click.echo("Error: --client is required. Specify which AI client to configure.\n")
        click.echo("Available clients:")
        click.echo("  mnemo init --client kiro         # Kiro CLI (hooks + skills + MCP)")
        click.echo("  mnemo init --client cursor       # Cursor (.cursorrules + MCP)")
        click.echo("  mnemo init --client claude-code  # Claude Code (CLAUDE.md + hooks + MCP)")
        click.echo("  mnemo init --client amazonq      # Amazon Q (.amazonq/rules + MCP)")
        click.echo("  mnemo init --client copilot      # GitHub Copilot (MCP)")
        click.echo("  mnemo init --client generic      # Any MCP-compatible agent")
        click.echo("  mnemo init --client all          # Configure all clients")
        raise SystemExit(1)

    from .init import init as do_init

    result = do_init(Path(path).resolve(), client=client)
    click.echo(result)
    click.echo("")
    if client == "kiro":
        click.echo("Next: Start a Kiro session:")
        click.echo("  kiro-cli chat --agent mnemo-enhanced")
    elif client == "claude-code":
        click.echo("Next: Start Claude Code in this directory.")
    elif client == "cursor":
        click.echo("Next: Open this folder in Cursor.")
    else:
        click.echo(f"Next: Start your AI client ({client}) in this directory.")


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
def map(path: str):
    """Regenerate the repo map from the graph DB."""
    from .config import mnemo_path
    from .init import _generate_legacy_files

    repo_root = Path(path).resolve()
    if not mnemo_path(repo_root).exists():
        click.echo("Not initialized. Run `mnemo init` first.")
        return
    _generate_legacy_files(repo_root)
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

    # Remove only Mnemo-owned Kiro files (not entire directories)
    click.echo("⏳ Removing Mnemo-generated files...")
    mnemo_kiro_files = [
        repo_root / ".kiro" / "hooks" / "agent-spawn.sh",
        repo_root / ".kiro" / "hooks" / "user-prompt-submit.sh",
        repo_root / ".kiro" / "hooks" / "pre-tool-use.sh",
        repo_root / ".kiro" / "hooks" / "post-tool-use.sh",
        repo_root / ".kiro" / "hooks" / "stop.sh",
        repo_root / ".kiro" / "agents" / "mnemo-enhanced.json",
        repo_root / ".kiro" / "skills" / "mnemo" / "SKILL.md",
        repo_root / ".kiro" / "settings" / "mcp.json",
    ]
    for f in mnemo_kiro_files:
        if f.exists():
            f.unlink()
            click.echo(f"  ✓ Removed {f.relative_to(repo_root)}")

    # Clean up empty directories left behind
    for d in [
        repo_root / ".kiro" / "skills" / "mnemo",
        repo_root / ".kiro" / "hooks",
        repo_root / ".kiro" / "agents",
        repo_root / ".kiro" / "skills",
        repo_root / ".kiro" / "settings",
    ]:
        if d.exists() and not any(d.iterdir()):
            d.rmdir()

    # Remove Mnemo entries from .claude/settings.json (don't delete the file)
    claude_settings = repo_root / ".claude" / "settings.json"
    if claude_settings.exists():
        import json
        try:
            data = json.loads(claude_settings.read_text(encoding="utf-8"))
            changed = False
            if "hooks" in data:
                del data["hooks"]
                changed = True
            if "mcpServers" in data and "mnemo" in data["mcpServers"]:
                del data["mcpServers"]["mnemo"]
                if not data["mcpServers"]:
                    del data["mcpServers"]
                changed = True
            if changed:
                claude_settings.write_text(json.dumps(data, indent=2), encoding="utf-8")
                click.echo("  ✓ Removed Mnemo hooks/MCP from .claude/settings.json")
        except (json.JSONDecodeError, OSError):
            pass

    # Remove CLAUDE.md Mnemo section (or whole file if it's only Mnemo content)
    claude_md = repo_root / "CLAUDE.md"
    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        marker = "## Mnemo — Persistent Memory"
        if marker in content:
            before = content.split(marker)[0].rstrip()
            if before:
                claude_md.write_text(before + "\n", encoding="utf-8")
            else:
                claude_md.unlink()
            click.echo("  ✓ Removed Mnemo section from CLAUDE.md")

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
@click.option("--port", "-p", default=3333, help="Port to serve on.")
@click.option("--no-open", is_flag=True, help="Don't auto-open browser.")
@click.argument("path", default=".", type=click.Path(exists=True))
def ui(path: str, port: int, no_open: bool):
    """Open the Mnemo dashboard in your browser. (Alias for `mnemo serve`)"""
    from .serve import serve as start_server

    repo_root = Path(path).resolve()
    start_server(repo_root, port=port)


# --- Hive: shared team knowledge ---

@cli.group()
def hive():
    """Shared team knowledge. Contribute, search, and sync."""
    pass


@hive.command("init")
@click.option("--repo", "-r", default="", help="Git URL of shared hive repo")
@click.argument("path", default=".", type=click.Path(exists=True))
def hive_init(repo: str, path: str):
    """Initialize Hive — clone or create the shared knowledge repo."""
    import subprocess

    hive_dir = Path.home() / ".mnemo" / "hive"

    if hive_dir.exists():
        click.echo(f"Hive already initialized at {hive_dir}")
        click.echo("Run `mnemo hive pull` to sync latest.")
        return

    if repo:
        click.echo(f"Cloning hive from {repo}...")
        subprocess.run(["git", "clone", repo, str(hive_dir)], check=True)
    else:
        click.echo("Creating local hive...")
        hive_dir.mkdir(parents=True, exist_ok=True)
        # Copy templates from package
        import shutil
        pkg_hive = Path(__file__).parent.parent / "hive"
        if pkg_hive.exists():
            for item in ["templates", "knowledge", "README.md"]:
                src = pkg_hive / item
                dst = hive_dir / item
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                elif src.is_file():
                    shutil.copy2(src, dst)
        subprocess.run(["git", "init"], cwd=str(hive_dir), check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=str(hive_dir), check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "hive: initialize"], cwd=str(hive_dir), check=True, capture_output=True)

    click.echo(f"✅ Hive initialized at {hive_dir}")


@hive.command()
def pull():
    """Pull latest team knowledge from remote."""
    import subprocess

    hive_dir = Path.home() / ".mnemo" / "hive"
    if not hive_dir.exists():
        click.echo("Hive not initialized. Run `mnemo hive init` first.")
        return

    result = subprocess.run(
        ["git", "pull", "--ff-only"],
        cwd=str(hive_dir),
        capture_output=True, text=True
    )
    if result.returncode == 0:
        click.echo(f"✅ Hive synced. {result.stdout.strip()}")
    else:
        click.echo(f"⚠️ Pull failed (using cached): {result.stderr.strip()}")


@hive.command()
@click.argument("query")
def search(query: str):
    """Search team knowledge in Hive."""
    hive_dir = Path.home() / ".mnemo" / "hive" / "knowledge"
    if not hive_dir.exists():
        click.echo("Hive not initialized. Run `mnemo hive init` first.")
        return

    # Simple grep-based search across all knowledge files
    results = []
    for md_file in hive_dir.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        if query.lower() in content.lower():
            # Extract title from frontmatter
            title = md_file.stem.replace("-", " ").title()
            for line in content.split("\n"):
                if line.startswith("title:"):
                    title = line.split(":", 1)[1].strip().strip('"')
                    break
            rel_path = md_file.relative_to(hive_dir)
            results.append((title, str(rel_path)))

    if not results:
        click.echo(f"No results for '{query}' in Hive.")
        return

    click.echo(f"Found {len(results)} result(s):\n")
    for title, path in results:
        click.echo(f"  📄 {title}")
        click.echo(f"     {path}\n")


@hive.command()
@click.option("--type", "-t", "content_type", type=click.Choice(["fix", "decided", "pitfall", "howto"]), prompt=True)
@click.option("--title", prompt=True)
@click.option("--domain", prompt=True, default="general")
@click.option("--content", "-c", default="", help="Pre-filled content (from agent/session)")
@click.argument("path", default=".", type=click.Path(exists=True))
def contribute(content_type: str, title: str, domain: str, content: str, path: str):
    """Contribute knowledge to the team Hive."""
    import subprocess
    import datetime

    hive_dir = Path.home() / ".mnemo" / "hive"
    if not hive_dir.exists():
        click.echo("Hive not initialized. Run `mnemo hive init` first.")
        return

    # Read template
    template_file = hive_dir / "templates" / f"{content_type}.md"
    if not template_file.exists():
        template_file = Path(__file__).parent.parent / "hive" / "templates" / f"{content_type}.md"

    template = template_file.read_text(encoding="utf-8") if template_file.exists() else ""

    # Fill frontmatter
    slug = title.lower().replace(" ", "-").replace("/", "-")[:50]
    today = datetime.date.today().isoformat()
    contributor = subprocess.run(
        ["git", "config", "user.name"], capture_output=True, text=True
    ).stdout.strip() or "unknown"

    template = template.replace('title: ""', f'title: "{title}"')
    template = template.replace("domain: ", f"domain: {domain}")
    template = template.replace("contributed_by: ", f"contributed_by: {contributor}")
    template = template.replace("date: ", f"date: {today}")

    # If content provided (from agent), fill the template body
    if content:
        # Replace template placeholder sections with actual content
        # Simple approach: append content after frontmatter
        frontmatter_end = template.rfind("---")
        if frontmatter_end > 0:
            template = template[:frontmatter_end + 3] + "\n\n" + content
        else:
            template = template + "\n\n" + content

    # Determine target directory
    type_dirs = {"fix": "fixes", "decided": "decided", "pitfall": "pitfalls", "howto": "howtos"}
    target_dir = hive_dir / "knowledge" / type_dirs[content_type]
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{slug}.md"

    target_file.write_text(template, encoding="utf-8")

    if content:
        # Auto-filled by agent — commit directly
        click.echo(f"✅ Hive entry created: {target_file.relative_to(hive_dir)}")
        subprocess.run(["git", "add", str(target_file)], cwd=str(hive_dir), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"hive: add {content_type} - {title}"],
            cwd=str(hive_dir), capture_output=True
        )
        click.echo("   Committed. Run `git push` in hive to share with team.")
    else:
        # Manual mode — open editor
        import os
        editor = os.environ.get("EDITOR", "code")
        click.echo(f"\n📝 Template created at: {target_file}")
    click.echo("   Edit it, then run:")
    click.echo(f"   cd {hive_dir} && git add . && git commit -m 'hive: add {content_type} - {title}'")
    click.echo("   git push\n")

    # Try to open in editor
    try:
        subprocess.run([editor, str(target_file)], check=False)
    except FileNotFoundError:
        pass


# --- Learnings commands (rebuilt from previous session) ---

LEARNING_TYPES = ("architecture", "pattern", "pitfall", "tool", "investigation", "preference", "operational")


@cli.command("learn")
@click.option("--type", "-t", "learn_type", required=True, type=click.Choice(LEARNING_TYPES), help="Learning type.")
@click.option("--key", "-k", required=True, help="Short key (lowercase-with-hyphens).")
@click.option("--insight", "-i", required=True, help="What you learned (>20 chars).")
@click.option("--confidence", "-c", default=8, type=int, help="Confidence 1-10.")
@click.option("--source", "-s", default="observed", type=click.Choice(("observed", "user-stated", "inferred")))
@click.argument("path", default=".", type=click.Path(exists=True))
def learn(learn_type: str, key: str, insight: str, confidence: int, source: str, path: str):
    """Store a typed learning with key-based dedup."""
    import json as json_mod
    import re
    import time as time_mod
    from datetime import datetime, timezone

    from .config import mnemo_path
    from .core.injection import has_injection

    repo_root = Path(path).resolve()
    learnings_path = mnemo_path(repo_root) / "learnings.json"

    # Validation
    if not re.match(r'^[a-zA-Z0-9_-]+$', key):
        raise click.ClickException("Key must be alphanumeric with hyphens/underscores only.")
    if len(insight) < 20:
        raise click.ClickException("Insight must be >20 characters.")
    if has_injection(insight):
        raise click.ClickException("Rejected: insight contains injection pattern.")
    if confidence < 1 or confidence > 10:
        raise click.ClickException("Confidence must be 1-10.")

    # Load existing
    learnings = []
    if learnings_path.exists():
        try:
            learnings = json_mod.loads(learnings_path.read_text(encoding="utf-8"))
        except (json_mod.JSONDecodeError, OSError):
            learnings = []

    # Key-based dedup (latest wins)
    dedup_key = f"{key}|{learn_type}"
    learnings = [l for l in learnings if f"{l.get('key', '')}|{l.get('type', '')}" != dedup_key]

    entry = {
        "type": learn_type,
        "key": key,
        "insight": insight,
        "confidence": confidence,
        "source": source,
        "trusted": source == "user-stated",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "files": [],
    }
    learnings.append(entry)

    learnings_path.parent.mkdir(parents=True, exist_ok=True)
    learnings_path.write_text(json_mod.dumps(learnings, indent=2), encoding="utf-8")
    click.echo(f"✅ [{learn_type}:{key}] {insight[:60]}")


@cli.command("learnings")
@click.option("--type", "-t", "learn_type", default=None, type=click.Choice(LEARNING_TYPES), help="Filter by type.")
@click.option("--limit", "-l", default=10, help="Max results.")
@click.argument("path", default=".", type=click.Path(exists=True))
def learnings(learn_type: str | None, limit: int, path: str):
    """List stored learnings (sorted by confidence)."""
    import json as json_mod

    from .config import mnemo_path

    repo_root = Path(path).resolve()
    learnings_path = mnemo_path(repo_root) / "learnings.json"

    if not learnings_path.exists():
        click.echo("No learnings yet.")
        return

    entries = json_mod.loads(learnings_path.read_text(encoding="utf-8"))
    if learn_type:
        entries = [e for e in entries if e.get("type") == learn_type]

    entries.sort(key=lambda e: e.get("confidence", 0), reverse=True)
    entries = entries[:limit]

    if not entries:
        click.echo("No learnings found.")
        return

    for e in entries:
        click.echo(f"  [{e.get('type')}:{e.get('key')}] (conf:{e.get('confidence')}) {e.get('insight', '')[:70]}")


@cli.command("ingest")
@click.option("--file", "session_file", default=None, help="Specific session .jsonl file.")
@click.option("--dry-run", is_flag=True, help="Show what would be extracted without storing.")
@click.argument("path", default=".", type=click.Path(exists=True))
def ingest(session_file: str | None, dry_run: bool, path: str):
    """ETL: Extract learnings from Kiro session transcripts."""
    import json as json_mod
    import re
    import time as time_mod
    from datetime import datetime, timezone

    from .config import mnemo_path

    repo_root = Path(path).resolve()
    mnemo_dir = mnemo_path(repo_root)

    # Find session file (CWD-filtered)
    if session_file:
        session_path = Path(session_file)
    else:
        sessions_dir = Path.home() / ".kiro" / "sessions" / "cli"
        if not sessions_dir.exists():
            raise click.ClickException(f"No sessions directory: {sessions_dir}")

        # Filter to sessions whose CWD matches this repo
        repo_str = str(repo_root)
        files = sorted(sessions_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        matched_files = []
        for f in files:
            meta = f.with_suffix(".json")
            if meta.exists():
                try:
                    meta_data = json_mod.loads(meta.read_text())
                    session_cwd = meta_data.get("cwd", "")
                    if session_cwd and str(Path(session_cwd).resolve()) == repo_str:
                        matched_files.append(f)
                except (json_mod.JSONDecodeError, OSError):
                    pass
                if len(matched_files) >= 5:
                    break

        if not matched_files:
            matched_files = files[:1]  # Fallback
        if not matched_files:
            raise click.ClickException("No session files found.")
        session_path = matched_files[0]

    # Check watermark (don't re-process)
    watermark_file = mnemo_dir / ".ingest-watermark.json"
    watermark = {}
    if watermark_file.exists():
        try:
            watermark = json_mod.loads(watermark_file.read_text())
        except (json_mod.JSONDecodeError, OSError):
            pass

    session_id = session_path.stem
    session_mtime = session_path.stat().st_mtime
    last_processed = watermark.get(session_id, {}).get("mtime", 0)

    if session_mtime <= last_processed and not dry_run:
        click.echo(f"Session {session_id[:8]} already processed. Skipping.")
        return

    click.echo(f"Ingesting: {session_path.name} ({session_path.stat().st_size // 1024}KB)")

    # Parse session — extract assistant messages
    assistant_texts = []
    try:
        with open(session_path) as f:
            for line in f:
                try:
                    event = json_mod.loads(line)
                    if event.get("kind") == "AssistantMessage":
                        content = event.get("data", {}).get("content", [])
                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and item.get("kind") == "text":
                                    text = item.get("data", "")
                                    if len(text) > 50:
                                        assistant_texts.append(text)
                except (json_mod.JSONDecodeError, TypeError):
                    pass
    except OSError as e:
        raise click.ClickException(f"Failed to read session: {e}")

    click.echo(f"Found {len(assistant_texts)} assistant messages")

    # Extract learnings via pattern matching
    learnings_found = []
    decisions_found = []

    for text in assistant_texts:
        lower = text.lower()
        # Architecture patterns
        if any(w in lower for w in ("architecture", "pattern is", "structured as", "uses .* pattern", "convention")):
            match = re.search(r'(?:architecture|structured as|uses .+ pattern|convention)[^.]*\.', text, re.I)
            if match and len(match.group()) > 30:
                learnings_found.append(("architecture", match.group().strip()[:200]))
        # Decisions
        if any(w in lower for w in ("decided to", "going with", "chose", "i'll use")):
            match = re.search(r'(?:decided to|going with|chose|i\'ll use)[^.]*\.', text, re.I)
            if match and len(match.group()) > 20:
                decisions_found.append(match.group().strip()[:200])
        # Bug fixes
        if "root cause" in lower or ("the issue was" in lower and "fix" in lower):
            match = re.search(r'(?:root cause|the issue was|the problem was)[^.]*\.', text, re.I)
            if match and len(match.group()) > 25:
                learnings_found.append(("investigation", match.group().strip()[:200]))

    total = len(learnings_found) + len(decisions_found)
    click.echo(f"Extracted {total} learnings")

    if dry_run:
        for ltype, insight in learnings_found:
            click.echo(f"  [{ltype}] {insight[:70]}")
        for dec in decisions_found:
            click.echo(f"  [decision] {dec[:70]}")
        return

    # Store learnings
    stored_l = 0
    stored_d = 0
    for ltype, insight in learnings_found:
        key = re.sub(r'[^a-z0-9]+', '-', insight[:30].lower()).strip('-')
        try:
            from .core.injection import has_injection
            if has_injection(insight):
                continue
            # Use the learn logic inline
            ctx = click.Context(learn, info_name="learn")
            ctx.invoke(learn, learn_type=ltype, key=key, insight=insight, confidence=7, source="observed", path=path)
            stored_l += 1
        except (click.ClickException, SystemExit):
            pass

    for dec in decisions_found:
        try:
            from .memory.store import add_decision
            add_decision(repo_root, dec)
            stored_d += 1
        except (ValueError, Exception):
            pass

    click.echo(f"✅ Stored {stored_l} learnings, {stored_d} decisions")

    # Update watermark
    watermark[session_id] = {"mtime": session_mtime, "processed_at": time_mod.time()}
    watermark_file.parent.mkdir(parents=True, exist_ok=True)
    watermark_file.write_text(json_mod.dumps(watermark, indent=2), encoding="utf-8")


if __name__ == "__main__":
    cli()
