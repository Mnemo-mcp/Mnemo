"""Mnemo CLI – persistent memory for Amazon Q chats."""

from pathlib import Path

import click


@click.group()
def cli():
    """Mnemo – Persistent memory and repo map for Amazon Q."""
    pass


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
def init(path: str):
    """Initialize .mnemo/ in the current repo. Just run: mnemo init"""
    from .init import init as do_init
    result = do_init(Path(path).resolve())
    click.echo(result)


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
def map(path: str):
    """Regenerate the repo map."""
    from .repo_map import save_repo_map
    from .config import mnemo_path
    repo_root = Path(path).resolve()
    if not mnemo_path(repo_root).exists():
        click.echo("Not initialized. Run `mnemo init` first.")
        return
    save_repo_map(repo_root)
    click.echo("✓ Repo map updated.")


@cli.command()
@click.argument("content")
@click.option("--category", "-c", default="general")
@click.argument("path", default=".", type=click.Path(exists=True))
def remember(content: str, category: str, path: str):
    """Store a memory entry. Example: mnemo remember 'uses FastAPI'"""
    from .memory import add_memory
    entry = add_memory(Path(path).resolve(), content, category)
    click.echo(f"✓ Remembered #{entry['id']}: {content}")


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
@click.argument("path", default=".", type=click.Path(exists=True))
@click.confirmation_option(prompt="This will delete all Mnemo memory. Are you sure?")
def reset(path: str):
    """Wipe all Mnemo data and start fresh. Run: mnemo reset"""
    import shutil
    from .config import mnemo_path
    repo_root = Path(path).resolve()
    base = mnemo_path(repo_root)
    if base.exists():
        shutil.rmtree(base)
        click.echo("✓ .mnemo/ deleted. Run `mnemo init` to start fresh.")
    else:
        click.echo("Nothing to reset — .mnemo/ not found.")


if __name__ == "__main__":
    cli()
